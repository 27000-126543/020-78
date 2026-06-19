import os
import sys
from datetime import datetime

from compliance_checker.rumor_checker import check_rumors, summarize_rumors_by_scope, list_departments
from compliance_checker.chat_analyzer import analyze_chat_file, analyze_chat_folder
from compliance_checker.report_generator import generate_daily_report, generate_short_report


def print_header(session_info):
    print()
    print("=" * 60)
    print("        证券营业部合规巡检工具 v1.1")
    print("=" * 60)
    if session_info.get("department"):
        dept = session_info["department"]
        rumor_done = "✓" if session_info.get("rumor_done") else "✗"
        chat_done = "✓" if session_info.get("chat_done") else "✗"
        print(f"  当前营业部：{dept}    舆情[{rumor_done}]  群聊[{chat_done}]")
        print("=" * 60)
    print()


def print_menu():
    print("请选择功能：")
    print()
    print("  1. 市场传闻与舆情排查")
    print("  2. 群聊文本核查")
    print("  3. 生成合规日报")
    print("  4. 设置营业部名称")
    print("  0. 退出")
    print()


def color_text(text, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    if color not in colors:
        return text
    return f"{colors[color]}{text}{colors['reset']}"


def risk_label(level):
    labels = {
        "high": ("【高风险】", "red"),
        "medium": ("【中风险】", "yellow"),
        "low": ("【低风险】", "green"),
    }
    text, color = labels.get(level, ("【未知】", "blue"))
    return color_text(text, color)


def run_set_department(session_info):
    print()
    print(color_text("--- 设置营业部 ---", "bold"))
    print()
    depts = list_departments()
    print("可选营业部：")
    for i, d in enumerate(depts, 1):
        print(f"  {i}. {d}")
    print()
    choice = input("请输入编号或直接输入营业部名称（回车跳过）：").strip()
    if not choice:
        return
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(depts):
            session_info["department"] = depts[idx]
            print()
            print(color_text(f"已设置：{depts[idx]}", "green"))
        else:
            print(color_text("编号无效。", "red"))
    else:
        session_info["department"] = choice
        print()
        print(color_text(f"已设置：{choice}", "green"))
    print()


def run_rumor_check(session_info):
    print()
    print(color_text("--- 市场传闻与舆情排查 ---", "bold"))
    print()
    default_kw = session_info.get("department", "")
    hint = f"（当前营业部：{default_kw}，回车使用该关键字）" if default_kw else ""
    prompt = f"请输入营业部/客户经理/股票简称{hint}："
    keyword = input(prompt).strip()

    if not keyword:
        keyword = default_kw if default_kw else None

    print()
    print("正在排查中...")
    print()

    data = check_rumors(keyword=keyword)
    results = data["results"]

    if not results:
        print(color_text("未发现相关风险信息。", "green"))
        scope_summary = summarize_rumors_by_scope(data)
        if scope_summary:
            print(f"排查覆盖：营业部{scope_summary['dept_count']}个 / "
                  f"经理{scope_summary['manager_count']}人 / "
                  f"股票{scope_summary['stock_count']}只 / "
                  f"客户群{scope_summary['group_count']}个")
        print()
        session_info["rumor_data"] = data
        session_info["rumor_done"] = True
        return data

    scope_summary = summarize_rumors_by_scope(data)
    if scope_summary:
        print(color_text(
            f"覆盖范围：{scope_summary['dept_count']}个营业部 / "
            f"{scope_summary['manager_count']}名客户经理 / "
            f"{scope_summary['stock_count']}只股票标的 / "
            f"{scope_summary['group_count']}个客户群",
            "cyan"
        ))
        if keyword:
            print(f"筛选关键词：{keyword}")
    print(color_text(f"共发现 {len(results)} 条风险信息，按发生时间从近到远排列：", "yellow"))
    print("-" * 60)

    for i, r in enumerate(results, 1):
        time_str = r["time"].strftime("%Y-%m-%d %H:%M")
        print()
        dept = r.get("department", "-")
        print(f"{i}. {risk_label(r['highest_risk'])} {color_text(dept, 'blue')} | "
              f"{color_text(r['source'], 'cyan')} | {r['manager']} | {time_str}")
        if r.get("stock"):
            print(f"   涉及标的：{r['stock']}")
        print(f"   内容摘要：{r['content']}")
        print(f"   风险类型：{'、'.join(r['risk_categories'])}")
        if r["sensitive_matches"]:
            matched = [m["matched_keywords"] for m in r["sensitive_matches"]]
            flat_matched = [kw for sublist in matched for kw in sublist]
            print(f"   敏感词：{color_text('、'.join(flat_matched), 'red')}")

    print()
    print("-" * 60)

    high_count = sum(1 for r in results if r["highest_risk"] == "high")
    medium_count = sum(1 for r in results if r["highest_risk"] == "medium")
    print(f"  高风险：{color_text(str(high_count) + ' 条', 'red')}    "
          f"中风险：{color_text(str(medium_count) + ' 条', 'yellow')}")
    print()

    session_info["rumor_data"] = data
    session_info["rumor_done"] = True
    return data


def _display_single_chat_result(result):
    total = result["total_lines"]
    violations = result["violation_count"]
    fname = result.get("file_name", "未知文件")

    print(color_text(f"【{fname}】检查完成：共 {total} 条消息，发现 {violations} 条违规", "yellow"))
    print("-" * 60)

    if violations == 0:
        print()
        print(color_text("  未发现违规内容，合规状态良好。", "green"))
        print()
        return

    high_count = sum(1 for v in result["violations"] if v["highest_risk"] == "high")
    medium_count = sum(1 for v in result["violations"] if v["highest_risk"] == "medium")

    print()
    print(f"  高风险：{color_text(str(high_count) + ' 条', 'red')}    "
          f"中风险：{color_text(str(medium_count) + ' 条', 'yellow')}")
    print()

    print("违规详情：")
    print()
    for i, v in enumerate(result["violations"], 1):
        categories = "、".join([m["category"] for m in v["sensitive_matches"]])
        print(f"  [{i}] {risk_label(v['highest_risk'])} 第{v['line_number']}行 | {v['timestamp']} | {v['speaker']}")
        print(f"      原句：{v['content']}")
        print(f"      类型：{categories}")
        print(f"      建议：{color_text(v['suggestion'], 'cyan')}")
        print()

    print("-" * 60)

    if result["speaker_stats"]:
        print()
        print("发言统计：")
        for speaker, stats in result["speaker_stats"].items():
            print(f"  {speaker}：共{stats['total']}条，违规{stats['violations']}条")
        print()


def _display_folder_chat_result(data):
    print(color_text(f"批量扫描完成：共扫描 {data['file_count']} 个文件，"
                     f"合计 {data['total_lines']} 条消息，"
                     f"发现 {data['total_violations']} 条违规内容", "yellow"))
    print("-" * 60)
    print()
    print("文件汇总：")
    print()

    for i, fres in enumerate(data["file_results"], 1):
        fname = fres.get("file_name", "未知")
        if not fres.get("performed"):
            print(f"  {i}. {color_text(fname, 'red')}  分析失败：{fres.get('error', '未知错误')}")
            continue
        total = fres.get("total_lines", 0)
        vc = fres.get("violation_count", 0)
        hc = sum(1 for v in fres.get("violations", []) if v["highest_risk"] == "high")
        mc = sum(1 for v in fres.get("violations", []) if v["highest_risk"] == "medium")
        if vc > 0:
            flag = color_text(f"🔴 高{hc}/中{mc}", "red") if hc > 0 else color_text(f"🟡 中{mc}", "yellow")
        else:
            flag = color_text("✅ 合规", "green")
        print(f"  {i}. {fname}  {total}条消息  违规{vc}条  {flag}")

    print()
    print("-" * 60)

    if data["high_risk_violations"]:
        print()
        print(color_text("需优先处理的高风险内容：", "red"))
        print()
        for i, v in enumerate(data["high_risk_violations"], 1):
            fname = v.get("file_name", "")
            categories = "、".join([m["category"] for m in v["sensitive_matches"]])
            print(f"  [{i}] {color_text(fname, 'cyan')} 第{v['line_number']}行 | {v['timestamp']} | {v['speaker']}")
            print(f"      {risk_label('high')} {v['content']}")
            print(f"      类型：{categories}")
            print(f"      建议：{v['suggestion']}")
            print()

        print("-" * 60)

    agg = data.get("aggregate")
    if agg and agg.get("speaker_stats"):
        print()
        print("总体发言统计（按违规数排序）：")
        sorted_speakers = sorted(
            agg["speaker_stats"].items(),
            key=lambda x: x[1]["violations"],
            reverse=True
        )
        for speaker, stats in sorted_speakers:
            if stats["violations"] > 0:
                print(f"  {speaker}：共{stats['total']}条，违规{color_text(str(stats['violations']) + '条', 'red')}")
            else:
                print(f"  {speaker}：共{stats['total']}条，违规0条")
        print()


def run_chat_analysis(session_info):
    print()
    print(color_text("--- 群聊文本核查 ---", "bold"))
    print()
    print("请选择输入方式：")
    print("  1. 使用示例数据演示")
    print("  2. 单文件模式（拖拽文件到窗口）")
    print("  3. 批量文件夹模式（拖拽文件夹到窗口，一次扫描多份记录）")
    print()

    choice = input("请选择（默认1）：").strip() or "1"

    if choice == "1":
        print()
        print("正在分析示例聊天记录...")
        print()
        results = analyze_chat_file(use_sample=True)
        _display_single_chat_result(results)
        session_info["chat_data"] = results
        session_info["chat_done"] = True
        return results

    elif choice == "2":
        file_path = input("请输入聊天记录文件路径（可拖拽）：").strip().strip('"').strip("'")
        if not file_path:
            print(color_text("未输入文件路径。", "red"))
            return None

        if not os.path.exists(file_path):
            print(color_text(f"文件不存在：{file_path}", "red"))
            return None

        if os.path.isdir(file_path):
            print(color_text("该路径是文件夹，请使用批量模式（选项3）。", "yellow"))
            return None

        print()
        print(f"正在分析 {os.path.basename(file_path)} ...")
        print()

        try:
            results = analyze_chat_file(file_path=file_path)
        except Exception as e:
            print(color_text(f"分析失败：{str(e)}", "red"))
            print()
            return None

        _display_single_chat_result(results)
        session_info["chat_data"] = results
        session_info["chat_done"] = True
        return results

    elif choice == "3":
        folder_path = input("请输入聊天记录文件夹路径（可拖拽）：").strip().strip('"').strip("'")
        if not folder_path:
            print(color_text("未输入文件夹路径。", "red"))
            return None

        if not os.path.exists(folder_path):
            print(color_text(f"文件夹不存在：{folder_path}", "red"))
            return None

        if not os.path.isdir(folder_path):
            print(color_text("该路径不是文件夹，请使用单文件模式（选项2）。", "yellow"))
            return None

        print()
        print(f"正在批量扫描 {folder_path} ...")
        print()

        try:
            data = analyze_chat_folder(folder_path)
        except Exception as e:
            print(color_text(f"批量扫描失败：{str(e)}", "red"))
            print()
            return None

        if data["file_count"] == 0:
            print(color_text("文件夹内未找到 .txt / .log / .csv 格式的聊天记录文件。", "yellow"))
            print()
            return None

        _display_folder_chat_result(data)
        session_info["chat_data"] = data
        session_info["chat_done"] = True
        return data

    else:
        print(color_text("无效选项。", "red"))
        return None


def run_report_generation(session_info):
    print()
    print(color_text("--- 生成合规日报 ---", "bold"))
    print()

    dept_name = session_info.get("department")
    if not dept_name:
        dept_name = input("请输入营业部名称：").strip()
    else:
        change = input(f"当前营业部：{dept_name}，回车确认或输入新名称：").strip()
        if change:
            dept_name = change
            session_info["department"] = dept_name
    if not dept_name:
        dept_name = "XX证券营业部"

    rumor_data = session_info.get("rumor_data")
    chat_data = session_info.get("chat_data")
    rumor_done = session_info.get("rumor_done", False)
    chat_done = session_info.get("chat_done", False)

    if not rumor_done and not chat_done:
        print()
        print(color_text("⚠ 尚未执行任何检查，建议先运行功能1和功能2，再生成日报。", "yellow"))
        confirm = input("是否仍要生成日报？(y/n，默认n)：").strip().lower()
        if confirm != "y":
            return None
    elif not rumor_done or not chat_done:
        missing = []
        if not rumor_done:
            missing.append("舆情排查")
        if not chat_done:
            missing.append("群聊核查")
        print()
        print(color_text(f"⚠ 尚未完成：{'、'.join(missing)}，日报中将标记为【未检查】。", "yellow"))
        input("按回车键继续生成...")

    print()
    print("正在生成日报...")
    print()

    full_report = generate_daily_report(dept_name, rumor_data, chat_data)
    short_report = generate_short_report(dept_name, rumor_data, chat_data)

    print(color_text("【简短版（适合直接粘贴合规日志）】", "bold"))
    print("-" * 60)
    print()
    print(short_report)
    print()
    print("-" * 60)
    print()
    view_full = input("是否查看完整版日报？(y/n，默认y)：").strip().lower()
    if view_full != "n":
        print()
        print("=" * 60)
        print(color_text("【完整版合规巡检日报】", "bold"))
        print("=" * 60)
        print()
        print(full_report)
        print()
        print("=" * 60)
        print()

    print("保存选项：")
    print("  1. 仅保存简短版")
    print("  2. 仅保存完整版")
    print("  3. 两个版本都保存")
    print("  0. 不保存")
    print()
    save_choice = input("请选择（默认0）：").strip() or "0"

    date_str = datetime.now().strftime("%Y%m%d")
    saved_files = []

    try:
        if save_choice in ["1", "3"]:
            short_name = f"合规巡检日报_简短版_{date_str}.txt"
            with open(short_name, "w", encoding="utf-8") as f:
                f.write(short_report)
            saved_files.append(short_name)

        if save_choice in ["2", "3"]:
            full_name = f"合规巡检日报_完整版_{date_str}.txt"
            with open(full_name, "w", encoding="utf-8") as f:
                f.write(full_report)
            saved_files.append(full_name)
    except Exception as e:
        print(color_text(f"保存失败：{str(e)}", "red"))

    if saved_files:
        print()
        print(color_text("已保存文件：", "green"))
        for fname in saved_files:
            print(f"  {os.path.abspath(fname)}")
    print()

    return {"full": full_report, "short": short_report}


def main():
    session_info = {
        "department": None,
        "rumor_data": None,
        "rumor_done": False,
        "chat_data": None,
        "chat_done": False,
    }

    print_header(session_info)

    while True:
        print_menu()
        choice = input("请输入选项编号：").strip()

        if choice == "0":
            print()
            print("感谢使用，再见！")
            print()
            break
        elif choice == "1":
            run_rumor_check(session_info)
        elif choice == "2":
            run_chat_analysis(session_info)
        elif choice == "3":
            run_report_generation(session_info)
        elif choice == "4":
            run_set_department(session_info)
        else:
            print()
            print(color_text("无效选项，请重新选择。", "red"))
            print()
            continue

        print_header(session_info)
        input(color_text("按回车键继续...", "blue"))
        print_header(session_info)


if __name__ == "__main__":
    main()
