from datetime import datetime


def generate_daily_report(business_department, rumor_results, chat_results, check_date=None):
    if check_date is None:
        check_date = datetime.now().strftime("%Y年%m月%d日")

    report_lines = []
    report_lines.append(f"【{business_department}合规巡检日报】")
    report_lines.append(f"检查日期：{check_date}")
    report_lines.append("-" * 50)

    report_lines.append("一、检查范围")
    report_lines.append(f"1. 市场传闻与舆情监测：覆盖重点客户经理、客户群及相关股票标的")
    if rumor_results:
        report_lines.append(f"   - 共排查舆情信息 {len(rumor_results)} 条")
    else:
        report_lines.append("   - 今日未发现相关舆情信息")

    if chat_results:
        report_lines.append(f"2. 客户群聊内容核查：")
        report_lines.append(f"   - 共检查聊天记录 {chat_results['total_lines']} 条")
        report_lines.append(f"   - 涉及发言人员 {len(chat_results['speaker_stats'])} 人")
    else:
        report_lines.append("2. 客户群聊内容核查：今日未开展群聊文本核查")

    report_lines.append("-" * 50)
    report_lines.append("二、发现问题")

    high_risk_count = 0
    medium_risk_count = 0
    all_categories = set()

    if rumor_results:
        for r in rumor_results:
            if r["highest_risk"] == "high":
                high_risk_count += 1
            elif r["highest_risk"] == "medium":
                medium_risk_count += 1
            for cat in r["risk_categories"]:
                all_categories.add(cat)

    if chat_results and chat_results["violations"]:
        for v in chat_results["violations"]:
            if v["highest_risk"] == "high":
                high_risk_count += 1
            elif v["highest_risk"] == "medium":
                medium_risk_count += 1
            for m in v["sensitive_matches"]:
                all_categories.add(m["category"])

    total_issues = high_risk_count + medium_risk_count

    if total_issues == 0:
        report_lines.append("今日巡检未发现重大合规风险问题。")
    else:
        report_lines.append(f"今日共发现合规风险问题 {total_issues} 项，其中：")
        report_lines.append(f"  - 高风险问题：{high_risk_count} 项")
        report_lines.append(f"  - 中风险问题：{medium_risk_count} 项")
        report_lines.append("")
        report_lines.append("主要风险类型：")
        for i, cat in enumerate(sorted(all_categories), 1):
            report_lines.append(f"  {i}. {cat}")

        report_lines.append("")
        report_lines.append("具体问题清单：")

        issue_num = 1
        if rumor_results:
            report_lines.append("【舆情监测类】")
            for r in rumor_results:
                risk_label = "高风险" if r["highest_risk"] == "high" else "中风险"
                report_lines.append(
                    f"  {issue_num}. [{risk_label}] {r['source']} - {r['manager']} "
                    f"({r['time'].strftime('%m-%d %H:%M')})"
                )
                report_lines.append(f"     内容摘要：{r['content'][:40]}...")
                report_lines.append(f"     涉及类型：{'、'.join(r['risk_categories'])}")
                issue_num += 1

        if chat_results and chat_results["violations"]:
            report_lines.append("【群聊核查类】")
            for v in chat_results["violations"]:
                risk_label = "高风险" if v["highest_risk"] == "high" else "中风险"
                categories = "、".join([m["category"] for m in v["sensitive_matches"]])
                report_lines.append(
                    f"  {issue_num}. [{risk_label}] 第{v['line_number']}行 - {v['speaker']} "
                    f"({v['timestamp']})"
                )
                report_lines.append(f"     违规内容：{v['content'][:50]}...")
                report_lines.append(f"     涉及类型：{categories}")
                issue_num += 1

    report_lines.append("-" * 50)
    report_lines.append("三、处置状态")

    if total_issues == 0:
        report_lines.append("今日无待处置事项，日常监控正常。")
    else:
        report_lines.append("已采取的处置措施：")
        report_lines.append("  1. 对高风险问题已第一时间通知相关客户经理核实")
        report_lines.append("  2. 涉嫌违规表述已要求立即删除并补发风险揭示")
        report_lines.append("  3. 涉及客户投诉维权事项已启动客诉处理流程")
        report_lines.append("  4. 所有问题已登记台账，持续跟踪整改情况")

    report_lines.append("-" * 50)
    report_lines.append("四、待跟进事项")

    follow_ups = []
    if rumor_results:
        high_risk_rumors = [r for r in rumor_results if r["highest_risk"] == "high"]
        for r in high_risk_rumors[:3]:
            follow_ups.append(f"跟进 {r['manager']} 相关舆情核实及处置进展")

    if chat_results and chat_results["violations"]:
        high_risk_violations = [v for v in chat_results["violations"] if v["highest_risk"] == "high"]
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

    report_lines.append("-" * 50)
    report_lines.append(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"合规专员：__________（签字）")

    return "\n".join(report_lines)
