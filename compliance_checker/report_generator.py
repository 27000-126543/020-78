from datetime import datetime
from collections import Counter
from .ledger import STATUS_PENDING, STATUS_REMINDED, STATUS_RECTIFIED


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


def generate_daily_report(business_department, rumor_data, chat_data, check_date=None, ledger=None):
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
                status_str = _lookup_ledger_status(ledger, r.get("content", ""), "舆情", r.get("manager"), r.get("source")) if ledger else "待核实"
                last_action_str = _format_last_action(ledger, r.get("content", ""), "舆情", r.get("manager"), r.get("source"))
                report_lines.append(
                    f"  {issue_num}. [{risk_label}][{status_str}] {dept} / {r['source']} / {r['manager']} "
                    f"({r['time'].strftime('%m-%d %H:%M')})"
                )
                if r.get("stock"):
                    report_lines.append(f"     涉及标的：{r['stock']}")
                report_lines.append(f"     内容摘要：{r['content'][:50]}...")
                report_lines.append(f"     涉及类型：{'、'.join(r['risk_categories'])}")
                if last_action_str:
                    report_lines.append(f"     最近处理：{last_action_str}")
                issue_num += 1

        if chat_performed and chat_agg and chat_agg.get("violations"):
            report_lines.append("【群聊核查类】")
            for v in chat_agg["violations"]:
                risk_label = "高风险" if v["highest_risk"] == "high" else "中风险"
                categories = "、".join([m["category"] for m in v["sensitive_matches"]])
                loc = f"第{v['line_number']}行"
                v_file = v.get("file_name", "")
                if v_file:
                    loc = f"{v_file} / {loc}"
                status_str = _lookup_ledger_status(ledger, v.get("content", ""), "群聊", v.get("speaker"), v_file) if ledger else "待核实"
                last_action_str = _format_last_action(ledger, v.get("content", ""), "群聊", v.get("speaker"), v_file)
                report_lines.append(
                    f"  {issue_num}. [{risk_label}][{status_str}] {loc} - {v['speaker']} ({v['timestamp']})"
                )
                report_lines.append(f"     违规内容：{v['content'][:50]}...")
                report_lines.append(f"     涉及类型：{categories}")
                if last_action_str:
                    report_lines.append(f"     最近处理：{last_action_str}")
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
        if ledger:
            status_summary = ledger.get_status_summary()
            report_lines.append("处置状态汇总：")
            for s in ["待核实", "已提醒", "已整改"]:
                cnt = status_summary.get(s, 0)
                report_lines.append(f"  - {s}：{cnt} 项")
            report_lines.append("")
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


def generate_short_report(business_department, rumor_data, chat_data, check_date=None, ledger=None):
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

    if ledger and total_issues > 0:
        status_summary = ledger.get_status_summary()
        disposition = (
            f"待核实{status_summary.get('待核实', 0)}项、"
            f"已提醒{status_summary.get('已提醒', 0)}项、"
            f"已整改{status_summary.get('已整改', 0)}项"
        )
    elif total_issues > 0:
        disposition = "已通知相关客户经理整改，违规内容要求删除并补发风险揭示；台账登记完毕"
    else:
        disposition = "日常监控正常"

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


def _find_ledger_item(ledger, content, source_type, manager=None, source_detail=None):
    if not ledger or not content:
        return None
    content_stripped = content.strip()
    for item in ledger.items:
        if item.get("content", "").strip() == content_stripped:
            if item.get("source") == source_type:
                if manager and item.get("manager", "-") != manager:
                    continue
                if source_detail and item.get("source_detail", "-") != source_detail:
                    continue
                return item
    for item in ledger.items:
        if item.get("content", "").strip() == content_stripped:
            if item.get("source") == source_type:
                if manager and item.get("manager", "-") != manager:
                    continue
                return item
    for item in ledger.items:
        if item.get("content", "").strip() == content_stripped:
            return item
    return None


def _format_last_action(ledger, content, source_type, manager=None, source_detail=None):
    item = _find_ledger_item(ledger, content, source_type, manager, source_detail)
    if not item:
        return None
    history = item.get("history", [])
    if not history:
        return None
    last = history[-1]
    parts = []
    if last.get("time"):
        parts.append(last["time"])
    if last.get("action_type"):
        parts.append(last["action_type"])
    if last.get("note"):
        parts.append(f"备注：{last['note']}")
    if last.get("reviewer"):
        parts.append(f"复核：{last['reviewer']}")
    return " | ".join(parts) if parts else None


def _lookup_ledger_status(ledger, content, source_type, manager=None, source_detail=None):
    item = _find_ledger_item(ledger, content, source_type, manager, source_detail)
    if not item:
        return "待核实"
    return item.get("status", "待核实")


def generate_trend_report(business_department, days=7, historical_data=None, ledger=None, filter_department=None, filter_manager=None):
    if historical_data is None:
        from .sample_data import generate_historical_rumors
        historical_data = generate_historical_rumors(days)

    if not historical_data:
        return "无历史数据可供趋势分析。"

    filter_scope_parts = []
    if filter_department:
        filter_scope_parts.append(f"营业部：{filter_department}")
    if filter_manager:
        filter_scope_parts.append(f"客户经理：{filter_manager}")
    filter_scope_str = f"（专项：{'；'.join(filter_scope_parts)}）" if filter_scope_parts else ""

    lines = []
    lines.append(f"【{business_department} 合规风险周会复盘{filter_scope_str}】")
    lines.append(f"统计范围：近 {len(historical_data)} 天")
    if filter_scope_parts:
        lines.append(f"筛选条件：{'；'.join(filter_scope_parts)}")
    lines.append("=" * 60)

    lines.append("")
    lines.append("一、高风险数量变化")
    lines.append("-" * 60)
    lines.append(f"  {'日期':<14} {'高风险':>6} {'中风险':>6} {'合计':>6}")
    lines.append("  " + "-" * 36)
    for d in historical_data:
        lines.append(
            f"  {d['date']:<14} {d['high_risk_count']:>6} {d['medium_risk_count']:>6} {d['total_count']:>6}"
        )

    high_counts = [d["high_risk_count"] for d in historical_data]
    total_counts = [d["total_count"] for d in historical_data]
    avg_high = sum(high_counts) / len(high_counts) if high_counts else 0
    avg_total = sum(total_counts) / len(total_counts) if total_counts else 0
    trend = "上升" if len(high_counts) >= 2 and high_counts[0] > high_counts[-1] else \
            "下降" if len(high_counts) >= 2 and high_counts[0] < high_counts[-1] else "持平"
    lines.append("  " + "-" * 36)
    lines.append(f"  日均高风险：{avg_high:.1f} 条  日均总量：{avg_total:.1f} 条  整体趋势：{trend}")

    lines.append("")
    lines.append("二、重复出现客户经理")
    lines.append("-" * 60)
    manager_counter = Counter()
    for d in historical_data:
        for mgr in d.get("managers", []):
            if filter_manager and filter_manager.lower() not in mgr.lower():
                continue
            manager_counter[mgr] += 1
    repeat_managers = [(m, c) for m, c in manager_counter.most_common() if c > 1]
    if repeat_managers:
        for mgr, count in repeat_managers:
            lines.append(f"  {mgr}：近{len(historical_data)}天出现 {count} 次")
    else:
        lines.append("  无重复出现客户经理")

    lines.append("")
    lines.append("三、高频敏感词")
    lines.append("-" * 60)
    keyword_counter = Counter()
    for d in historical_data:
        for kw in d.get("top_keywords", []):
            keyword_counter[kw] += 1
    top_keywords = keyword_counter.most_common(10)
    if top_keywords:
        for i, (kw, count) in enumerate(top_keywords, 1):
            lines.append(f"  {i}. {kw}（出现 {count} 天）")
    else:
        lines.append("  无高频敏感词数据")

    lines.append("")
    lines.append("四、待整改台账")
    lines.append("-" * 60)
    if ledger:
        filtered_items = ledger.items[:]
        if filter_department:
            filtered_items = [i for i in filtered_items if filter_department.lower() in i.get("department", "").lower()]
        if filter_manager:
            filtered_items = [i for i in filtered_items if filter_manager.lower() in i.get("manager", "").lower()]

        pending = [i for i in filtered_items if i.get("status") == STATUS_PENDING]
        reminded = [i for i in filtered_items if i.get("status") == STATUS_REMINDED]
        rectified = [i for i in filtered_items if i.get("status") == STATUS_RECTIFIED]

        lines.append(f"  待核实：{len(pending)} 项")
        lines.append(f"  已提醒未整改：{len(reminded)} 项")
        lines.append(f"  已整改：{len(rectified)} 项")

        dept_dist = {}
        mgr_dist = {}
        for item in pending + reminded:
            d = item.get("department", "-")
            dept_dist[d] = dept_dist.get(d, 0) + 1
            m = item.get("manager", "-")
            mgr_dist[m] = mgr_dist.get(m, 0) + 1

        if dept_dist:
            lines.append("")
            lines.append("  按营业部分布：")
            for dept, cnt in sorted(dept_dist.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"    - {dept}：{cnt} 项")
        if mgr_dist:
            lines.append("")
            lines.append("  按经理分布：")
            for mgr, cnt in sorted(mgr_dist.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"    - {mgr}：{cnt} 项")

        overdue = [i for i in filtered_items if i.get("status", "") in [STATUS_PENDING, STATUS_REMINDED]]
        if filter_department or filter_manager:
            overdue_lines = overdue[:10]
        else:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=3)
            cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
            overdue_lines = [i for i in overdue if i.get("added_at", "") < cutoff_str][:10]

        if overdue_lines:
            lines.append("")
            scope_note = "筛选条件下待处理" if (filter_department or filter_manager) else "超期3天未处理"
            lines.append(f"  {scope_note}（{len(overdue_lines)} 条）：")
            for item in overdue_lines:
                dept = item.get("department", "-")
                mgr = item.get("manager", "-")
                st = item.get("status", STATUS_PENDING)
                preview = item.get("content", "")[:30] + "..."
                lines.append(f"    [{item['id']}] [{st}] {dept} / {mgr} / {preview}")
    else:
        lines.append("  暂无台账数据")

    lines.append("")
    lines.append("五、重点关注建议")
    lines.append("-" * 60)
    suggestions = []
    if repeat_managers:
        top_mgr = repeat_managers[0][0]
        suggestions.append(f"重点关注 {top_mgr}，近期反复出现合规风险，建议安排合规谈话")
    if top_keywords:
        top_kw = top_keywords[0][0]
        suggestions.append(f"高频敏感词「{top_kw}」需在合规培训中重点强调")
    if trend == "上升":
        suggestions.append("高风险数量呈上升趋势，建议加强日常巡检频次")
    elif trend == "下降":
        suggestions.append("高风险数量呈下降趋势，继续保持现有合规管理力度")
    if ledger:
        total_pending = len([i for i in ledger.items if i.get("status") == STATUS_PENDING])
        if total_pending > 0:
            suggestions.append(f"当前有 {total_pending} 项待核实风险，建议尽快完成核实处置")
    if not suggestions:
        suggestions.append("整体合规态势平稳，持续日常监控即可")
    for i, s in enumerate(suggestions, 1):
        lines.append(f"  {i}. {s}")

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"报告类型：周会复盘材料{'（专项版本）' if filter_scope_parts else ''}")

    return "\n".join(lines)
