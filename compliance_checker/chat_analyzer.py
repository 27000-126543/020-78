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
        return analyze_chat_lines(lines)

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

    return analyze_chat_lines(lines)
