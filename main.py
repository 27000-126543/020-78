import os
import sys
from datetime import datetime

from compliance_checker.rumor_checker import check_rumors
from compliance_checker.chat_analyzer import analyze_chat_file
from compliance_checker.report_generator import generate_daily_report


def print_header():
    print()
    print("=" * 60)
    print("        证券营业部合规巡检工具 v1.0")
    print("=" * 60)
    print()


def print_menu():
    print("请选择功能：")
    print()
    print("  1. 市场传闻与舆情排查")
    print("  2. 群聊文本核查")
    print("  3. 生成合规日报")
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


def run_rumor_check():
    print()
    print(color_text("--- 市场传闻与舆情排查 ---", "bold"))
    print()
    keyword = input("请输入营业部/客户经理/股票简称（回车查看全部）：").strip()

    print()
    print("正在排查中...")
    print()

    results = check_rumors(keyword=keyword if keyword else None)

    if not results:
        print(color_text("未发现相关风险信息。", "green"))
        print()
        return results

    print(color_text(f"共发现 {len(results)} 条风险信息，按风险等级排序：", "yellow"))
    print("-" * 60)

    for i, r in enumerate(results, 1):
        time_str = r["time"].strftime("%Y-%m-%d %H:%M")
        print()
        print(f"{i}. {risk_label(r['highest_risk'])} {color_text(r['source'], 'cyan')} | {r['manager']} | {time_str}")
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
    print()
    return results


def run_chat_analysis():
    print()
    print(color_text("--- 群聊文本核查 ---", "bold"))
    print()
    print("请选择输入方式：")
    print("  1. 使用示例数据演示")
    print("  2. 输入文件路径（可拖拽文件到窗口）")
    print()

    choice = input("请选择（默认1）：").strip() or "1"

    if choice == "1":
        print()
        print("正在分析示例聊天记录...")
        print()
        results = analyze_chat_file(use_sample=True)
    else:
        file_path = input("请输入聊天记录文件路径：").strip().strip('"').strip("'")
        if not file_path:
            print(color_text("未输入文件路径。", "red"))
            return None

        if not os.path.exists(file_path):
            print(color_text(f"文件不存在：{file_path}", "red"))
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

    total = results["total_lines"]
    violations = results["violation_count"]

    print(color_text(f"检查完成！共检查 {total} 条消息，发现 {violations} 条违规内容。", "yellow"))
    print("-" * 60)

    if violations == 0:
        print()
        print(color_text("  未发现违规内容，合规状态良好。", "green"))
        print()
        return results

    high_count = sum(1 for v in results["violations"] if v["highest_risk"] == "high")
    medium_count = sum(1 for v in results["violations"] if v["highest_risk"] == "medium")

    print()
    print(f"  高风险：{color_text(str(high_count) + ' 条', 'red')}")
    print(f"  中风险：{color_text(str(medium_count) + ' 条', 'yellow')}")
    print()

    print("违规详情：")
    print()
    for i, v in enumerate(results["violations"], 1):
        categories = "、".join([m["category"] for m in v["sensitive_matches"]])
        print(f"  [{i}] {risk_label(v['highest_risk'])} 第{v['line_number']}行 | {v['timestamp']} | {v['speaker']}")
        print(f"      原句：{v['content']}")
        print(f"      类型：{categories}")
        print(f"      建议：{color_text(v['suggestion'], 'cyan')}")
        print()

    print("-" * 60)

    if results["speaker_stats"]:
        print()
        print("发言统计：")
        for speaker, stats in results["speaker_stats"].items():
            print(f"  {speaker}：共{stats['total']}条，违规{stats['violations']}条")
        print()

    return results


def run_report_generation(rumor_results=None, chat_results=None):
    print()
    print(color_text("--- 生成合规日报 ---", "bold"))
    print()

    dept_name = input("请输入营业部名称：").strip()
    if not dept_name:
        dept_name = "XX证券营业部"

    print()
    print("正在生成日报...")
    print()

    if rumor_results is None:
        rumor_results = check_rumors()
    if chat_results is None:
        chat_results = analyze_chat_file(use_sample=True)

    report = generate_daily_report(dept_name, rumor_results, chat_results)

    print("=" * 60)
    print()
    print(report)
    print()
    print("=" * 60)
    print()

    save_choice = input("是否保存日报到文件？(y/n，默认n)：").strip().lower()
    if save_choice == "y":
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"合规巡检日报_{date_str}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            print()
            print(color_text(f"日报已保存到：{os.path.abspath(filename)}", "green"))
        except Exception as e:
            print(color_text(f"保存失败：{str(e)}", "red"))
        print()

    return report


def main():
    rumor_results = None
    chat_results = None

    print_header()

    while True:
        print_menu()
        choice = input("请输入选项编号：").strip()

        if choice == "0":
            print()
            print("感谢使用，再见！")
            print()
            break
        elif choice == "1":
            rumor_results = run_rumor_check()
        elif choice == "2":
            chat_results = run_chat_analysis()
        elif choice == "3":
            run_report_generation(rumor_results, chat_results)
        else:
            print()
            print(color_text("无效选项，请重新选择。", "red"))
            print()
            continue

        input(color_text("按回车键继续...", "blue"))


if __name__ == "__main__":
    main()
