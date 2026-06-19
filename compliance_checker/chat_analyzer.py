import os
import re
from .sensitive_words import SENSITIVE_PATTERNS
from .sample_data import generate_sample_chat_lines


def parse_chat_line(line):
    pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[([^\]]+)\]\s+(.*)'
    match = re.match(pattern, line.strip())
    if match:
        return {
            "timestamp": match.group(1),
            "speaker": match.group(2),
            "content": match.group(3),
        }
    return None


def detect_sensitive_content(text):
    results = []
    for pattern in SENSITIVE_PATTERNS:
        matched_keywords = []
        for keyword in pattern["keywords"]:
            if keyword in text:
                matched_keywords.append(keyword)
        if matched_keywords:
            results.append({
                "category": pattern["category"],
                "risk_level": pattern["risk_level"],
                "matched_keywords": matched_keywords,
                "suggestion": pattern["suggestion"],
            })
    return results


def analyze_chat_lines(lines):
    violations = []
    total_lines = 0
    speaker_stats = {}

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        total_lines += 1

        parsed = parse_chat_line(line)
        if not parsed:
            continue

        speaker = parsed["speaker"]
        content = parsed["content"]
        timestamp = parsed["timestamp"]

        if speaker not in speaker_stats:
            speaker_stats[speaker] = {"total": 0, "violations": 0}
        speaker_stats[speaker]["total"] += 1

        sensitive_matches = detect_sensitive_content(content)
        if sensitive_matches:
            speaker_stats[speaker]["violations"] += 1
            highest_risk = min(
                sensitive_matches,
                key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["risk_level"]]
            )
            violations.append({
                "line_number": idx,
                "timestamp": timestamp,
                "speaker": speaker,
                "content": content,
                "sensitive_matches": sensitive_matches,
                "highest_risk": highest_risk["risk_level"],
                "suggestion": highest_risk["suggestion"],
            })

    violations.sort(
        key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x["highest_risk"]],
            x["line_number"]
        )
    )

    return {
        "total_lines": total_lines,
        "violation_count": len(violations),
        "violations": violations,
        "speaker_stats": speaker_stats,
    }


def analyze_chat_file(file_path=None, use_sample=False):
    if use_sample or not file_path:
        lines = generate_sample_chat_lines()
        result = analyze_chat_lines(lines)
        result["file_name"] = "示例数据"
        result["file_path"] = None
        result["performed"] = True
        return result

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    _, ext = os.path.splitext(file_path)
    if ext.lower() not in ['.txt', '.log', '.csv']:
        raise ValueError(f"不支持的文件格式: {ext}，请使用 .txt 或 .log 文件")

    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
    lines = None
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None:
        raise ValueError("无法识别文件编码，请转换为 UTF-8 格式后重试")

    result = analyze_chat_lines(lines)
    result["file_name"] = os.path.basename(file_path)
    result["file_path"] = file_path
    result["performed"] = True
    return result


def analyze_chat_folder(folder_path):
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"文件夹不存在: {folder_path}")

    if not os.path.isdir(folder_path):
        raise ValueError(f"路径不是文件夹: {folder_path}")

    valid_exts = ['.txt', '.log', '.csv']
    file_list = []
    for fname in os.listdir(folder_path):
        fpath = os.path.join(folder_path, fname)
        if os.path.isfile(fpath):
            _, ext = os.path.splitext(fname)
            if ext.lower() in valid_exts:
                file_list.append(fpath)

    if not file_list:
        return {
            "performed": True,
            "mode": "folder",
            "folder_path": folder_path,
            "file_count": 0,
            "file_results": [],
            "total_lines": 0,
            "total_violations": 0,
            "high_risk_violations": [],
            "aggregate": None,
        }

    file_results = []
    total_lines = 0
    total_violations = 0
    all_high_risk = []
    combined_violations = []
    combined_speaker_stats = {}

    for fpath in sorted(file_list):
        try:
            fres = analyze_chat_file(file_path=fpath)
            file_results.append(fres)
            total_lines += fres["total_lines"]
            total_violations += fres["violation_count"]

            for v in fres["violations"]:
                v_copy = v.copy()
                v_copy["file_name"] = fres["file_name"]
                v_copy["file_path"] = fres["file_path"]
                combined_violations.append(v_copy)
                if v["highest_risk"] == "high":
                    all_high_risk.append(v_copy)

            for speaker, stats in fres["speaker_stats"].items():
                if speaker not in combined_speaker_stats:
                    combined_speaker_stats[speaker] = {"total": 0, "violations": 0}
                combined_speaker_stats[speaker]["total"] += stats["total"]
                combined_speaker_stats[speaker]["violations"] += stats["violations"]
        except Exception as e:
            file_results.append({
                "file_name": os.path.basename(fpath),
                "file_path": fpath,
                "performed": False,
                "error": str(e),
            })

    combined_violations.sort(
        key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x["highest_risk"]],
            x["line_number"]
        )
    )
    all_high_risk.sort(
        key=lambda x: x["line_number"]
    )

    aggregate = {
        "total_lines": total_lines,
        "violation_count": total_violations,
        "violations": combined_violations,
        "speaker_stats": combined_speaker_stats,
        "file_name": f"{len(file_results)}个文件汇总",
        "file_path": folder_path,
        "performed": True,
    }

    duplicate_high_risk = _detect_duplicate_high_risk(all_high_risk)

    return {
        "performed": True,
        "mode": "folder",
        "folder_path": folder_path,
        "file_count": len(file_results),
        "file_results": file_results,
        "total_lines": total_lines,
        "total_violations": total_violations,
        "high_risk_violations": all_high_risk,
        "duplicate_high_risk": duplicate_high_risk,
        "aggregate": aggregate,
    }


def _detect_duplicate_high_risk(high_risk_violations):
    if not high_risk_violations:
        return []

    content_groups = {}
    for v in high_risk_violations:
        content = v["content"].strip()
        if content not in content_groups:
            content_groups[content] = {
                "content": content,
                "files": [],
                "speakers": set(),
                "count": 0,
                "categories": set(),
            }
        group = content_groups[content]
        if v.get("file_name") and v["file_name"] not in group["files"]:
            group["files"].append(v["file_name"])
        group["speakers"].add(v["speaker"])
        group["count"] += 1
        for m in v.get("sensitive_matches", []):
            group["categories"].add(m["category"])

    duplicates = []
    for group in content_groups.values():
        if group["count"] > 1 or len(group["files"]) > 1:
            duplicates.append({
                "content": group["content"],
                "count": group["count"],
                "files": sorted(group["files"]),
                "speakers": sorted(group["speakers"]),
                "categories": sorted(group["categories"]),
            })

    duplicates.sort(key=lambda x: x["count"], reverse=True)
    return duplicates
