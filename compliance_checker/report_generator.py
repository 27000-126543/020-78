from datetime import datetime


def _is_rumor_performed(rumor_data):
    return rumor_data is not None and rumor_data.get("performed") is True


def _get_rumor_list(rumor_data):
    if not _is_rumor_performed(rumor_data):
        return []
    return rumor_data.get("results", [])


def _is_chat_performed(chat_data):
    if chat_data is None:
        return False
    if chat_data.get("mode") == "folder":
        return chat_data.get("performed") is True
    return chat_data.get("performed") is True


def _get_chat_aggregate(chat_data):
    if not _is_chat_performed(chat_data):
        return None
    if chat_data.get("mode") == "folder":
        return chat_data.get("aggregate")
    return chat_data


def _collect_issues(rumor_data, chat_data):
    high_risk_count = 0
    medium_risk_count = 0
    all_categories = set()
    rumor_list = _get_rumor_list(rumor_data)
    chat_agg = _get_chat_aggregate(chat_data)

    for r in rumor_list:
        if r["highest_risk"] == "high":
            high_risk_count += 1
        elif r["highest_risk"] == "medium":
            medium_risk_count += 1
        for cat in r["risk_categories"]:
            all_categories.add(cat)

    if chat_agg and chat_agg.get("violations"):
        for v in chat_agg["violations"]:
            if v["highest_risk"] == "high":
                high_risk_count += 1
            elif v["highest_risk"] == "medium":
                medium_risk_count += 1
            for m in v["sensitive_matches"]:
                all_categories.add(m["category"])

    return high_risk_count, medium_risk_count, all_categories, rumor_list, chat_agg


def generate_daily_report(business_department, rumor_data, chat_data, check_date=None):
    if check_date is None:
        check_date = datetime.now().strftime("%Y年%m月%d日")

    rumor_performed = _is_rumor_performed(rumor_data)
    chat_performed = _is_chat_performed(chat_data)
    rumor_list = _get_rumor_list(rumor_data)
    chat_agg = _get_chat_aggregate(chat_data)
    high_count, medium_count, all_categories, _, _ = _collect_issues(rumor_data, chat_data)
    total_issues = high_count + medium_count

    report_lines = []
    report_lines.append(f"【{business_department}合规巡检日报】")
    report_lines.append(f"检查日期：{check_date}")
    report_lines.append("-" * 60)

    report_lines.append("一、检查范围")
    if rumor_performed:
        keyword = rumor_data.get("keyword")
        scope_desc = f"（关键词：{keyword}）" if keyword else "（全量）"
        report_lines.append(f"1. 市场传闻与舆情监测{scope_desc}：")
        report_lines.append(f"   - 覆盖重点客户经理、客户群及相关股票标的")
        report_lines.append(f"   - 共排查舆情信息 {len(rumor_list)} 条")
    else:
        report_lines.append("1. 市场传闻与舆情监测：【未检查】⚠ 请返回功能1补做舆情排查")

    if chat_performed:
        if chat_data.get("mode") == "folder":
            report_lines.append(f"2. 客户群聊内容核查：（批量模式）")
            report_lines.append(f"   - 共扫描聊天文件 {chat_data.get('file_count', 0)} 份")
            if chat_agg:
                report_lines.append(f"   - 合计检查聊天记录 {chat_agg['total_lines']} 条")
                report_lines.append(f"   - 涉及发言人员 {len(chat_agg['speaker_stats'])} 人")
        else:
            report_lines.append(f"2. 客户群聊内容核查：（单文件模式）")
            report_lines.append(f"   - 文件：{chat_agg.get('file_name', '未知') if chat_agg else '未知'}")
            if chat_agg:
                report_lines.append(f"   - 共检查聊天记录 {chat_agg['total_lines']} 条")
                report_lines.append(f"   - 涉及发言人员 {len(chat_agg['speaker_stats'])} 人")
    else:
        report_lines.append("2. 客户群聊内容核查：【未检查】⚠ 请返回功能2补做群聊核查")

    report_lines.append("-" * 60)
    report_lines.append("二、发现问题")

    if not rumor_performed and not chat_performed:
        report_lines.append("⚠ 舆情排查与群聊核查均未执行，无法汇总问题。请先完成功能1和功能2。")
    elif total_issues == 0:
        report_lines.append("今日巡检未发现合规风险问题。")
    else:
        report_lines.append(f"今日共发现合规风险问题 {total_issues} 项，其中：")
        report_lines.append(f"  - 高风险问题：{high_count} 项")
        report_lines.append(f"  - 中风险问题：{medium_count} 项")
        if all_categories:
            report_lines.append("")
            report_lines.append("主要风险类型：")
            for i, cat in enumerate(sorted(all_categories), 1):
                report_lines.append(f"  {i}. {cat}")

        report_lines.append("")
        report_lines.append("具体问题清单：")
        issue_num = 1

        if rumor_performed and rumor_list:
            report_lines.append("【舆情监测类】")
            for r in rumor_list:
                risk_label = "高风险" if r["highest_risk"] == "high" else "中风险"
                dept = r.get("department", "-")
                report_lines.append(
                    f"  {issue_num}. [{risk_label}] {dept} / {r['source']} / {r['manager']} "
                    f"({r['time'].strftime('%m-%d %H:%M')})"
                )
                if r.get("stock"):
                    report_lines.append(f"     涉及标的：{r['stock']}")
                report_lines.append(f"     内容摘要：{r['content'][:50]}...")
                report_lines.append(f"     涉及类型：{'、'.join(r['risk_categories'])}")
                issue_num += 1

        if chat_performed and chat_agg and chat_agg.get("violations"):
            report_lines.append("【群聊核查类】")
            for v in chat_agg["violations"]:
                risk_label = "高风险" if v["highest_risk"] == "high" else "中风险"
                categories = "、".join([m["category"] for m in v["sensitive_matches"]])
                loc = f"第{v['line_number']}行"
                if v.get("file_name"):
                    loc = f"{v['file_name']} / {loc}"
                report_lines.append(
                    f"  {issue_num}. [{risk_label}] {loc} - {v['speaker']} ({v['timestamp']})"
                )
                report_lines.append(f"     违规内容：{v['content'][:50]}...")
                report_lines.append(f"     涉及类型：{categories}")
                issue_num += 1

    report_lines.append("-" * 60)
    report_lines.append("三、处置状态")

    pending_items = []
    if not rumor_performed:
        pending_items.append("补做市场传闻与舆情排查")
    if not chat_performed:
        pending_items.append("补做客户群聊文本核查")

    if pending_items:
        report_lines.append("⚠ 以下检查尚未完成，处置待完善：")
        for i, item in enumerate(pending_items, 1):
            report_lines.append(f"  {i}. {item}")
        report_lines.append("")

    if total_issues == 0:
        report_lines.append("今日无待处置事项，日常监控正常。")
    else:
        report_lines.append("已采取的处置措施：")
        report_lines.append("  1. 对高风险问题已第一时间通知相关客户经理核实")
        report_lines.append("  2. 涉嫌违规表述已要求立即删除并补发风险揭示")
        report_lines.append("  3. 涉及客户投诉维权事项已启动客诉处理流程")
        report_lines.append("  4. 所有问题已登记台账，持续跟踪整改情况")

    report_lines.append("-" * 60)
    report_lines.append("四、待跟进事项")

    follow_ups = []
    if rumor_performed:
        high_risk_rumors = [r for r in rumor_list if r["highest_risk"] == "high"]
        managers_seen = set()
        for r in high_risk_rumors[:3]:
            if r["manager"] not in managers_seen:
                dept = r.get("department", "")
                follow_ups.append(f"跟进 {dept} {r['manager']} 相关舆情核实及处置进展")
                managers_seen.add(r["manager"])

    if chat_performed and chat_agg and chat_agg.get("violations"):
        high_risk_violations = [v for v in chat_agg["violations"] if v["highest_risk"] == "high"]
        speakers = set()
        for v in high_risk_violations:
            speakers.add(v["speaker"])
        for s in list(speakers)[:2]:
            follow_ups.append(f"跟进 {s} 违规内容整改及合规培训")

    if not follow_ups:
        follow_ups.append("持续监测市场动态及客户群舆情，防范合规风险")
        follow_ups.append("定期开展合规培训，强化客户经理合规意识")

    for i, item in enumerate(follow_ups, 1):
        report_lines.append(f"  {i}. {item}")

    report_lines.append("-" * 60)
    report_lines.append(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"合规专员：__________（签字）")

    return "\n".join(report_lines)


def generate_short_report(business_department, rumor_data, chat_data, check_date=None):
    if check_date is None:
        check_date = datetime.now().strftime("%Y-%m-%d")

    rumor_performed = _is_rumor_performed(rumor_data)
    chat_performed = _is_chat_performed(chat_data)
    high_count, medium_count, all_categories, rumor_list, chat_agg = _collect_issues(rumor_data, chat_data)
    total_issues = high_count + medium_count

    scope_parts = []
    if rumor_performed:
        scope_parts.append(f"舆情排查{len(rumor_list)}条")
    else:
        scope_parts.append("舆情排查【未检查】")
    if chat_performed:
        if chat_agg:
            scope_parts.append(f"群聊核查{chat_agg['total_lines']}条")
        else:
            scope_parts.append("群聊核查0条")
    else:
        scope_parts.append("群聊核查【未检查】")

    if total_issues == 0:
        issue_desc = "未发现合规风险"
    else:
        cats = "、".join(sorted(all_categories)) if all_categories else "合规风险"
        issue_desc = f"发现{total_issues}项问题（高风险{high_count}项、中风险{medium_count}项），涉及{cats}"

    if rumor_performed and rumor_list:
        depts = sorted({r.get("department", "") for r in rumor_list if r.get("department")})
        dept_desc = f"，覆盖{'、'.join(depts)}" if depts else ""
    else:
        dept_desc = ""

    disposition = "已通知相关客户经理整改，违规内容要求删除并补发风险揭示；客诉事项已启动处理流程；台账登记完毕" if total_issues > 0 else "日常监控正常"

    if not rumor_performed or not chat_performed:
        disposition += "（部分检查未完成，待补做）"

    follow_items = []
    if not rumor_performed:
        follow_items.append("补做舆情排查")
    if not chat_performed:
        follow_items.append("补做群聊核查")
    if total_issues > 0:
        follow_items.append("跟踪整改完成情况")
    else:
        follow_items.append("持续监控舆情及群聊")
    follow_desc = "；".join(follow_items)

    report = (
        f"【{business_department} {check_date} 合规巡检】\n"
        f"检查范围：{'；'.join(scope_parts)}{dept_desc}\n"
        f"发现问题：{issue_desc}\n"
        f"处置状态：{disposition}\n"
        f"待跟进：{follow_desc}\n"
        f"报告人：__________"
    )

    return report
