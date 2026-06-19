import os
import sys
from datetime import datetime

from compliance_checker.rumor_checker import check_rumors, summarize_rumors_by_scope, list_departments
from compliance_checker.chat_analyzer import analyze_chat_file, analyze_chat_folder
from compliance_checker.report_generator import (
    generate_daily_report, generate_short_report, generate_trend_report
)
from compliance_checker.ledger import RiskLedger, STATUS_PENDING, STATUS_REMINDED, STATUS_RECTIFIED, ALL_STATUSES


LEDGER_FILE = "risk_ledger.json"


def print_header(session_info):
    print()
    print("=" * 60)
    print("        证券营业部合规巡检工具 v1.4")
    print("=" * 60)
    dept = session_info.get("department")
    rumor_done = "✓" if session_info.get("rumor_done") else "✗"
    chat_done = "✓" if session_info.get("chat_done") else "✗"
    ledger = session_info.get("ledger")
    ledger_count = len(ledger.items) if ledger else 0
    if dept:
        print(f"  {dept}  舆情[{rumor_done}]  群聊[{chat_done}]  台账[{ledger_count}条]")
    else:
        print(f"  舆情[{rumor_done}]  群聊[{chat_done}]  台账[{ledger_count}条]")
    print("=" * 60)
    print()


def print_menu():
    print("请选择功能：")
    print()
    print("  1. 市场传闻与舆情排查")
    print("  2. 群聊文本核查")
    print("  3. 风险台账管理")
    print("  4. 生成合规日报 / 趋势汇总")
    print("  5. 设置营业部名称")
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


def status_label(status):
    colors = {
        STATUS_PENDING: "yellow",
        STATUS_REMINDED: "cyan",
        STATUS_RECTIFIED: "green",
    }
    return color_text(f"[{status}]", colors.get(status, "blue"))


def _save_ledger(session_info):
    ledger = session_info.get("ledger")
    if ledger:
        ledger.save_to_file(LEDGER_FILE)


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

    try:
        data = check_rumors(keyword=keyword)
    except Exception as e:
        print(color_text(f"排查异常：{str(e)}", "red"))
        print(color_text("已返回菜单，请重新操作。", "yellow"))
        print()
        return None

    results = data["results"]

    if not results:
        print(color_text(f"未发现相关风险信息。（关键词：{keyword or '全量'}）", "green"))
        scope_summary = summarize_rumors_by_scope(data)
        if scope_summary and scope_summary.get("dept_count", 0) > 0:
            print(f"排查覆盖：营业部{scope_summary.get('dept_count', 0)}个 / "
                  f"经理{scope_summary.get('manager_count', 0)}人 / "
                  f"股票{scope_summary.get('stock_count', 0)}只 / "
                  f"客户群{scope_summary.get('group_count', 0)}个")
        else:
            print("提示：当前关键词未匹配到任何营业部、客户经理或股票，请检查输入。")
        print()
        session_info["rumor_data"] = data
        session_info["rumor_done"] = True
        return data

    scope_summary = summarize_rumors_by_scope(data)
    if scope_summary:
        print(color_text(
            f"覆盖范围：{scope_summary.get('dept_count', 0)}个营业部 / "
            f"{scope_summary.get('manager_count', 0)}名客户经理 / "
            f"{scope_summary.get('stock_count', 0)}只股票标的 / "
            f"{scope_summary.get('group_count', 0)}个客户群",
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

    add_to_ledger = input("是否将风险结果录入台账？(y/n，默认y)：").strip().lower()
    if add_to_ledger != "n":
        added = session_info["ledger"].add_rumor_risks(data)
        _save_ledger(session_info)
        print(color_text(f"已录入台账 {added} 条。", "green"))
        print()

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
            flag = color_text(f"高{hc}/中{mc}", "red") if hc > 0 else color_text(f"中{mc}", "yellow")
        else:
            flag = color_text("合规", "green")
        print(f"  {i}. {fname}  {total}条消息  违规{vc}条  {flag}")

    print()
    print("-" * 60)

    duplicates = data.get("duplicate_high_risk", [])
    if duplicates:
        print()
        print(color_text("跨文件重复传播的高风险内容（按传播范围排序）：", "red"))
        print()
        for i, dup in enumerate(duplicates, 1):
            files_str = "、".join(dup["files"])
            speakers_str = "、".join(dup["speakers"])
            cats_str = "、".join(dup["categories"])
            fc_str = f'{dup["file_count"]}个文件'
            cnt_str = f'重复{dup["count"]}次'
            print(f"  [{i}] {color_text(cnt_str, 'red')} | 涉及{color_text(fc_str, 'yellow')}")
            print(f"      原句：{dup['content'][:60]}")
            print(f"      所在文件：{files_str}")
            print(f"      发言人：{speakers_str}")
            print(f"      风险类型：{cats_str}")
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

    else:
        print(color_text("无效选项。", "red"))
        return None

    add_to_ledger = input("是否将违规内容录入台账？(y/n，默认y)：").strip().lower()
    if add_to_ledger != "n":
        dept = session_info.get("department")
        if not dept:
            dept_input = input("当前未设置营业部，请输入关联营业部（回车跳过标记为未指定）：").strip()
            dept = dept_input if dept_input else None
        added = session_info["ledger"].add_chat_risks(session_info.get("chat_data"), department=dept)
        _save_ledger(session_info)
        print(color_text(f"已录入台账 {added} 条" + (f"（关联营业部：{dept}）" if dept else ""), "green"))
        print()

        chat_data_now = session_info.get("chat_data")
        if chat_data_now and chat_data_now.get("mode") == "folder":
            duplicates = chat_data_now.get("duplicate_high_risk", [])
            if duplicates:
                print(color_text(f"发现 {len(duplicates)} 个跨文件重复传播的高风险内容。", "yellow"))
                create_group = input("是否一键创建传播事件组？(y/n，默认y)：").strip().lower()
                if create_group != "n":
                    for dup in duplicates:
                        gid = session_info["ledger"].add_propagation_group(dup, department=dept)
                        print(f"  已创建传播事件组 #{gid}：{dup['content'][:30]}...")
                    _save_ledger(session_info)
                    print(color_text(f"已创建 {len(duplicates)} 个传播事件组。", "green"))
                print()
    print()

    return session_info.get("chat_data")


def run_ledger_management(session_info):
    ledger = session_info.get("ledger")
    if not ledger:
        ledger = RiskLedger()
        session_info["ledger"] = ledger

    while True:
        print()
        print(color_text("--- 风险台账管理 ---", "bold"))
        print()
        summary = ledger.get_status_summary()
        total = len(ledger.items)
        print(f"  台账总数：{total} 条")
        print(f"  {status_label(STATUS_PENDING)} {summary.get(STATUS_PENDING, 0)} 条    "
              f"{status_label(STATUS_REMINDED)} {summary.get(STATUS_REMINDED, 0)} 条    "
              f"{status_label(STATUS_RECTIFIED)} {summary.get(STATUS_RECTIFIED, 0)} 条")
        print()
        print("  1. 查看台账（可按营业部/经理/风险类型筛选）")
        print("  2. 闭环视图（近几天新增/已提醒/已整改/仍待核实）")
        print("  3. 更新处置状态")
        print("  4. 批量更新状态")
        print("  5. 追加整改记录（提醒/整改说明/复核结论）")
        print("  6. 查看传播事件组（跨文件重复内容汇总）")
        print("  0. 返回主菜单")
        print()

        choice = input("请选择：").strip()

        if choice == "0":
            break
        elif choice == "1":
            _ledger_view(ledger)
        elif choice == "2":
            _ledger_closure_view(ledger)
        elif choice == "3":
            _ledger_update_status(ledger)
            _save_ledger(session_info)
        elif choice == "4":
            _ledger_bulk_update(ledger)
            _save_ledger(session_info)
        elif choice == "5":
            _ledger_append_action(ledger)
            _save_ledger(session_info)
        elif choice == "6":
            _ledger_view_propagation_groups(ledger)
        else:
            print(color_text("无效选项。", "red"))


def _ledger_closure_view(ledger):
    print()
    days_input = input("查看近几天的闭环数据（默认7）：").strip()
    days = int(days_input) if days_input.isdigit() else 7

    closure = ledger.get_closure_view(days=days)
    print()
    print(color_text(f"--- 近 {days} 天台账闭环视图 ---", "bold"))
    print()
    print(f"  新增录入：{closure['total_added']} 条")
    print(f"  {status_label(STATUS_PENDING)} 待核实：{closure['pending']} 条")
    print(f"  {status_label(STATUS_REMINDED)} 已提醒：{closure['reminded']} 条")
    print(f"  {status_label(STATUS_RECTIFIED)} 已整改：{closure['rectified']} 条")

    if closure['total_added'] > 0:
        rect_rate = closure['rectified'] / closure['total_added'] * 100
        print(f"  整改率：{rect_rate:.1f}%")
    print()

    overdue_input = input("查看超过几天仍待处理的记录（待核实+已提醒未整改，默认3，回车跳过）：").strip()
    overdue_days = int(overdue_input) if overdue_input.isdigit() else 0
    if overdue_days > 0:
        overdue = ledger.get_overdue_items(overdue_days=overdue_days)
        if overdue:
            print()
            print(color_text(f"录入超过 {overdue_days} 天仍待处理的记录（{len(overdue)} 条）：", "red"))
            print("-" * 70)
            for item in overdue:
                dept = item.get("department", "-")
                mgr = item.get("manager", "-")
                st = item.get("status", STATUS_PENDING)
                preview = item.get("content", "")[:40] + "..."
                print(f"  [{item['id']}] {status_label(st)} {dept} / {mgr} / {preview}")
                print(f"       录入时间：{item.get('added_at', '-')}")
            print("-" * 70)
        else:
            print(color_text(f"没有超过 {overdue_days} 天仍待处理的记录。", "green"))
    print()


def _ledger_view(ledger):
    print()
    dept_filter = input("按营业部筛选（回车跳过）：").strip() or None
    mgr_filter = input("按客户经理筛选（回车跳过）：").strip() or None
    risk_filter = input("按风险类型筛选（回车跳过）：").strip() or None
    status_filter = input("按处置状态筛选（待核实/已提醒/已整改，回车跳过）：").strip() or None

    items = ledger.filter_items(
        department=dept_filter,
        manager=mgr_filter,
        risk_type=risk_filter,
        status=status_filter,
    )

    if not items:
        print()
        print(color_text("未找到匹配的台账记录。", "green"))
        print()
        return

    print()
    print(color_text(f"共 {len(items)} 条记录：", "yellow"))
    print("-" * 70)
    print(f"  {'序号':<4} {'来源':<4} {'营业部':<10} {'经理':<6} {'风险':<6} {'状态':<8} 内容摘要")
    print("  " + "-" * 64)

    for item in items:
        dept = item.get("department", "-")
        if dept == "-":
            dept = "(群聊)"
        mgr = item.get("manager", "-")
        risk = "高" if item.get("risk_level") == "high" else "中"
        status = item.get("status", STATUS_PENDING)
        content_preview = item.get("content", "")[:30] + "..."
        print(f"  {item['id']:<4} {item.get('source', '-'):<4} {dept:<10} {mgr:<6} "
              f"{risk:<6} {status:<8} {content_preview}")

    print("-" * 70)
    print()
    detail = input("输入序号查看详情（回车返回）：").strip()
    if detail.isdigit():
        item_id = int(detail)
        for item in items:
            if item["id"] == item_id:
                print()
                print(f"  序号：{item['id']}")
                print(f"  来源：{item.get('source', '-')} / {item.get('source_detail', '-')}")
                print(f"  营业部：{item.get('department', '-')}")
                print(f"  客户经理/发言人：{item.get('manager', '-')}")
                print(f"  风险等级：{item.get('risk_level', '-')}")
                print(f"  风险类型：{'、'.join(item.get('risk_categories', []))}")
                if item.get("stock"):
                    print(f"  涉及标的：{item['stock']}")
                print(f"  时间：{item.get('time', '-')}")
                print(f"  原句：{item.get('content', '')}")
                print(f"  处置状态：{status_label(item.get('status', STATUS_PENDING))}")
                print(f"  录入时间：{item.get('added_at', '-')}")
                if item.get("updated_at"):
                    print(f"  更新时间：{item['updated_at']}")
                if item.get("group_id"):
                    print(f"  所属传播事件组：#{item['group_id']}")
                history = item.get("history", [])
                if history:
                    print(f"  处置历史（{len(history)}条）：")
                    for idx, act in enumerate(history, 1):
                        parts = [act.get("time", "")]
                        if act.get("action_type"):
                            parts.append(f"[{act['action_type']}]")
                        if act.get("note"):
                            parts.append(f"备注：{act['note']}")
                        if act.get("reviewer"):
                            parts.append(f"复核：{act['reviewer']}")
                        print(f"    {idx}. {' | '.join(p for p in parts if p)}")
                print()
                break


def _ledger_update_status(ledger):
    print()
    item_id = input("请输入要更新的台账序号：").strip()
    if not item_id.isdigit():
        print(color_text("请输入有效数字。", "red"))
        return

    item_id = int(item_id)
    current = None
    for item in ledger.items:
        if item["id"] == item_id:
            current = item
            break

    if not current:
        print(color_text(f"未找到序号 {item_id} 的记录。", "red"))
        return

    print(f"当前状态：{status_label(current.get('status', STATUS_PENDING))}")
    print("可选状态：")
    for i, s in enumerate(ALL_STATUSES, 1):
        print(f"  {i}. {s}")
    new_choice = input("请选择新状态：").strip()
    if not new_choice.isdigit():
        print(color_text("未做更改。", "yellow"))
        return
    idx = int(new_choice) - 1
    if not (0 <= idx < len(ALL_STATUSES)):
        print(color_text("无效选项。", "red"))
        return
    note = input("处置备注（回车跳过）：").strip() or None
    reviewer = input("复核人（回车跳过）：").strip() or None
    if ledger.update_status(item_id, ALL_STATUSES[idx], note=note, reviewer=reviewer):
        print(color_text(f"已更新为：{ALL_STATUSES[idx]}", "green"))
    else:
        print(color_text("更新失败。", "red"))


def _ledger_bulk_update(ledger):
    print()
    print("批量更新方式：")
    print("  1. 按营业部更新所有记录")
    print("  2. 按客户经理更新所有记录")
    print("  3. 按风险类型更新所有记录")
    print()

    mode = input("请选择方式：").strip()

    if mode == "1":
        dept = input("请输入营业部名称：").strip()
        if not dept:
            return
        items = ledger.filter_items(department=dept)
    elif mode == "2":
        mgr = input("请输入客户经理姓名：").strip()
        if not mgr:
            return
        items = ledger.filter_items(manager=mgr)
    elif mode == "3":
        cats = ledger.get_risk_categories()
        if not cats:
            print("台账中无风险类型。")
            return
        print("可选风险类型：")
        for i, c in enumerate(cats, 1):
            print(f"  {i}. {c}")
        cat_choice = input("请选择：").strip()
        if cat_choice.isdigit():
            idx = int(cat_choice) - 1
            if 0 <= idx < len(cats):
                items = ledger.filter_items(risk_type=cats[idx])
            else:
                return
        else:
            return
    else:
        return

    if not items:
        print(color_text("未找到匹配记录。", "yellow"))
        return

    item_ids = [i["id"] for i in items]
    print(f"匹配到 {len(items)} 条记录，当前状态分布：")
    status_dist = {}
    for i in items:
        s = i.get("status", STATUS_PENDING)
        status_dist[s] = status_dist.get(s, 0) + 1
    for s, c in status_dist.items():
        print(f"  {s}：{c} 条")

    print("更新为：")
    for i, s in enumerate(ALL_STATUSES, 1):
        print(f"  {i}. {s}")
    new_choice = input("请选择新状态：").strip()
    if new_choice.isdigit():
        idx = int(new_choice) - 1
        if 0 <= idx < len(ALL_STATUSES):
            updated = ledger.bulk_update_status(item_ids, ALL_STATUSES[idx])
            print(color_text(f"已更新 {updated} 条记录为：{ALL_STATUSES[idx]}", "green"))
        else:
            print(color_text("无效选项。", "red"))


def _ledger_append_action(ledger):
    print()
    item_id = input("请输入要追加记录的台账序号：").strip()
    if not item_id.isdigit():
        print(color_text("请输入有效数字。", "red"))
        return
    item_id = int(item_id)
    current = None
    for item in ledger.items:
        if item["id"] == item_id:
            current = item
            break
    if not current:
        print(color_text(f"未找到序号 {item_id} 的记录。", "red"))
        return

    print(f"当前状态：{status_label(current.get('status', STATUS_PENDING))}")
    history = current.get("history", [])
    if history:
        print(f"已有处置记录：{len(history)} 条")

    print()
    print("可追加的动作类型：")
    action_options = ALL_STATUSES + ["追加备注", "合规复核"]
    for i, a in enumerate(action_options, 1):
        print(f"  {i}. {a}")
    act_choice = input("请选择动作类型（默认1 待核实）：").strip() or "1"
    if not act_choice.isdigit():
        print(color_text("无效选项。", "red"))
        return
    act_idx = int(act_choice) - 1
    if not (0 <= act_idx < len(action_options)):
        print(color_text("无效选项。", "red"))
        return
    action_type = action_options[act_idx]
    note = input("处置说明/整改备注（回车跳过）：").strip() or None
    reviewer = input("复核人（回车跳过）：").strip() or None

    if ledger.append_action(item_id, action_type, note=note, reviewer=reviewer):
        print(color_text(f"已追加记录：{action_type}", "green"))
    else:
        print(color_text("追加失败。", "red"))
    print()


def _ledger_view_propagation_groups(ledger):
    print()
    dept_filter = input("按营业部筛选传播事件组（回车跳过）：").strip() or None
    groups = ledger.get_propagation_groups(department=dept_filter)
    if not groups:
        print(color_text("暂无传播事件组。", "yellow"))
        print()
        return

    print()
    print(color_text(f"共 {len(groups)} 个传播事件组：", "yellow"))
    print("-" * 70)
    for g in groups:
        summary = ledger.get_group_summary(g["id"])
        status_parts = []
        for st, cnt in summary["status_distribution"].items():
            status_parts.append(f"{st}:{cnt}")
        print(f"  [#{g['id']}] {g['file_count']}个文件/重复{g['repeat_count']}次 | {g['content'][:40]}...")
        print(f"        文件：{'、'.join(g['files'])}")
        print(f"        发言人：{'、'.join(g['speakers'])}")
        print(f"        处置进度：{' / '.join(status_parts) if status_parts else '-'}")
    print("-" * 70)
    print()
    detail = input("输入事件组编号查看明细（回车返回）：").strip()
    if detail.isdigit():
        gid = int(detail)
        summary = ledger.get_group_summary(gid)
        if summary:
            print()
            g = summary["group"]
            print(color_text(f"--- 传播事件组 #{gid} 明细 ---", "bold"))
            print(f"  原句：{g['content']}")
            print(f"  涉及文件：{g['file_count']} 个 | 重复次数：{g['repeat_count']}")
            print(f"  文件列表：{'、'.join(g['files'])}")
            print(f"  发言人：{'、'.join(g['speakers'])}")
            print()
            print(f"  明细记录（{len(summary['members'])}条）：")
            for m in summary["members"]:
                print(f"    [{m['id']}] {status_label(m.get('status', STATUS_PENDING))} "
                      f"{m.get('source_detail', '-')} / {m.get('manager', '-')}")
            print()


def run_report_generation(session_info):
    print()
    print(color_text("--- 生成合规日报 / 趋势汇总 ---", "bold"))
    print()
    print("  1. 生成当日合规日报")
    print("  2. 生成趋势汇总报告（适合周会复盘）")
    print()
    choice = input("请选择（默认1）：").strip() or "1"

    if choice == "2":
        _run_trend_report(session_info)
        return

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
    ledger = session_info.get("ledger")

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

    full_report = generate_daily_report(dept_name, rumor_data, chat_data, ledger=ledger)
    short_report = generate_short_report(dept_name, rumor_data, chat_data, ledger=ledger)

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


def _run_trend_report(session_info):
    dept_name = session_info.get("department")
    if not dept_name:
        dept_name = input("请输入营业部名称：").strip()
    if not dept_name:
        dept_name = "XX证券营业部"

    days_input = input("请输入统计天数（默认7）：").strip()
    days = int(days_input) if days_input.isdigit() else 7

    print()
    print("专项筛选（回车跳过，使用全量数据）：")
    filter_dept = input("  按营业部筛选（回车跳过）：").strip() or None
    filter_mgr = input("  按客户经理筛选（回车跳过）：").strip() or None

    ledger = session_info.get("ledger")

    print()
    print("正在生成周会复盘材料...")
    print()

    report = generate_trend_report(
        dept_name,
        days=days,
        ledger=ledger,
        filter_department=filter_dept,
        filter_manager=filter_mgr,
    )

    print(report)
    print()

    preview_lines = report.split("\n")
    summary_preview = []
    for line in preview_lines:
        stripped = line.strip()
        if stripped.startswith("日均") or stripped.startswith("整体趋势"):
            summary_preview.append(stripped)
        elif stripped.startswith("重点关注") or stripped.startswith("1.") or stripped.startswith("2.") or stripped.startswith("3."):
            summary_preview.append(stripped)
    if summary_preview:
        print(color_text("摘要预览：", "bold"))
        for line in summary_preview[:5]:
            print(f"  {line}")
        print()

    save = input("是否保存周会复盘材料？(y/n，默认n)：").strip().lower()
    if save == "y":
        date_str = datetime.now().strftime("%Y%m%d")
        filter_suffix = ""
        if filter_dept:
            filter_suffix += f"_{filter_dept}"
        if filter_mgr:
            filter_suffix += f"_{filter_mgr}"
        filename = f"合规周会复盘_{days}天{filter_suffix}_{date_str}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            print(color_text(f"已保存到：{os.path.abspath(filename)}", "green"))
        except Exception as e:
            print(color_text(f"保存失败：{str(e)}", "red"))
    print()


def main():
    ledger = RiskLedger()
    if os.path.exists(LEDGER_FILE):
        ledger.load_from_file(LEDGER_FILE)

    session_info = {
        "department": None,
        "rumor_data": None,
        "rumor_done": False,
        "chat_data": None,
        "chat_done": False,
        "ledger": ledger,
    }

    print_header(session_info)

    while True:
        print_menu()
        choice = input("请输入选项编号：").strip()

        if choice == "0":
            _save_ledger(session_info)
            print()
            print("感谢使用，再见！")
            print()
            break
        elif choice == "1":
            run_rumor_check(session_info)
        elif choice == "2":
            run_chat_analysis(session_info)
        elif choice == "3":
            run_ledger_management(session_info)
        elif choice == "4":
            run_report_generation(session_info)
        elif choice == "5":
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
