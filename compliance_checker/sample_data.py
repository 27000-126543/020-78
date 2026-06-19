from datetime import datetime, timedelta

DEPARTMENTS = {
    "朝阳门营业部": ["张伟", "李娜", "王强"],
    "建国门营业部": ["赵敏", "刘洋", "陈静"],
    "中关村营业部": ["孙磊", "周芳", "吴昊"],
}

STOCK_BY_DEPT = {
    "朝阳门营业部": ["XX科技", "YY股份", "ZZ证券", "WW发展"],
    "建国门营业部": ["VV集团", "UU银行", "TT地产"],
    "中关村营业部": ["SS芯片", "RR医药", "QQ新能源"],
}


def generate_sample_rumors(keyword=None):
    today = datetime.now()
    rumors = []

    base_rumors = [
        {
            "source": "客户群A",
            "manager": "张伟",
            "department": "朝阳门营业部",
            "content": "今天有内部消息说XX科技要重组，大家可以关注一下，肯定涨",
            "time": today - timedelta(hours=2),
            "stock": "XX科技",
        },
        {
            "source": "客户群B",
            "manager": "李娜",
            "department": "朝阳门营业部",
            "content": "这支股票我保证收益至少20%，稳赚不赔，放心买",
            "time": today - timedelta(hours=5),
            "stock": "YY股份",
        },
        {
            "source": "客户群C",
            "manager": "王强",
            "department": "朝阳门营业部",
            "content": "最近行情不好，有客户亏了不少，说要投诉到证监会",
            "time": today - timedelta(hours=8),
            "stock": "ZZ证券",
        },
        {
            "source": "朋友圈",
            "manager": "张伟",
            "department": "朝阳门营业部",
            "content": "主力资金正在建仓，马上要拉升了，赶紧全仓买入",
            "time": today - timedelta(hours=12),
            "stock": "XX科技",
        },
        {
            "source": "客户群A",
            "manager": "张伟",
            "department": "朝阳门营业部",
            "content": "我帮你操作吧，账号密码告诉我，保证比你自己炒赚得多",
            "time": today - timedelta(days=1, hours=3),
            "stock": "WW发展",
        },
        {
            "source": "客户群D",
            "manager": "赵敏",
            "department": "建国门营业部",
            "content": "成为我们的VIP会员，每月只收3000服务费，保证月月盈利",
            "time": today - timedelta(days=1, hours=6),
            "stock": "",
        },
        {
            "source": "VIP客户群",
            "manager": "赵敏",
            "department": "建国门营业部",
            "content": "VV集团小道消息，有重磅利好即将公布，现在买入稳赚",
            "time": today - timedelta(days=1, hours=8),
            "stock": "VV集团",
        },
        {
            "source": "客户群B",
            "manager": "李娜",
            "department": "朝阳门营业部",
            "content": "这只股票目标价50元，现在才20，翻倍不是问题",
            "time": today - timedelta(days=1, hours=10),
            "stock": "YY股份",
        },
        {
            "source": "客户群E",
            "manager": "刘洋",
            "department": "建国门营业部",
            "content": "小道消息：某上市公司董事长被调查，还没公开",
            "time": today - timedelta(days=2, hours=5),
            "stock": "UU银行",
        },
        {
            "source": "客户群A",
            "manager": "张伟",
            "department": "朝阳门营业部",
            "content": "我们三七分成，我出消息你出钱，稳赚不亏",
            "time": today - timedelta(days=2, hours=8),
            "stock": "XX科技",
        },
        {
            "source": "高净值群",
            "manager": "陈静",
            "department": "建国门营业部",
            "content": "TT地产客户亏了40%，要维权起诉，大家注意沟通方式",
            "time": today - timedelta(days=2, hours=10),
            "stock": "TT地产",
        },
        {
            "source": "客户群F",
            "manager": "孙磊",
            "department": "中关村营业部",
            "content": "SS芯片有内幕，近期将公告重大订单，抓紧建仓",
            "time": today - timedelta(hours=3),
            "stock": "SS芯片",
        },
        {
            "source": "客户群G",
            "manager": "周芳",
            "department": "中关村营业部",
            "content": "RR医药我保证保本，亏了算我的，大胆买",
            "time": today - timedelta(hours=6),
            "stock": "RR医药",
        },
        {
            "source": "客户群H",
            "manager": "吴昊",
            "department": "中关村营业部",
            "content": "客户反映上周听了建议买入QQ新能源亏了很多，要求赔偿",
            "time": today - timedelta(hours=9),
            "stock": "QQ新能源",
        },
        {
            "source": "客户群C",
            "manager": "王强",
            "department": "朝阳门营业部",
            "content": "最近市场波动大，建议大家控制仓位，注意风险",
            "time": today - timedelta(days=2),
            "stock": "",
        },
    ]

    for r in base_rumors:
        if keyword:
            kw = keyword.lower()
            dept_match = kw in r["department"].lower()
            mgr_match = kw in r["manager"].lower()
            src_match = kw in r["source"].lower()
            content_match = kw in r["content"].lower()
            stock_match = kw in r["stock"].lower()
            if dept_match or mgr_match or src_match or content_match or stock_match:
                rumors.append(r)
        else:
            rumors.append(r)

    rumors.sort(key=lambda x: x["time"], reverse=True)
    return rumors


def generate_sample_chat_lines():
    lines = [
        "2026-06-20 09:15:23 [张伟] 大家早上好，今天盘面震荡注意风险",
        "2026-06-20 09:30:12 [张伟] XX科技今天可以关注，有内部消息要重组",
        "2026-06-20 09:45:33 [客户A] 张经理，上次你推荐的股票亏了不少怎么办",
        "2026-06-20 10:00:45 [张伟] 放心，这支股票我保证收益至少20%，稳赚不赔",
        "2026-06-20 10:15:22 [客户B] 真的假的？有这么准吗",
        "2026-06-20 10:20:18 [张伟] 主力资金正在建仓，马上要拉升了，赶紧全仓买入",
        "2026-06-20 10:35:09 [客户C] 我上次听你的全仓进去，现在亏了20万，要投诉你们",
        "2026-06-20 10:40:55 [张伟] 别着急，我帮你操作吧，账号密码告诉我，保证赚回来",
        "2026-06-20 11:00:00 [客户D] 怎么收费啊？有会员服务吗",
        "2026-06-20 11:05:33 [张伟] 成为VIP每月3000，我们三七分成，稳赚不亏",
        "2026-06-20 11:30:12 [客户E] 张经理，有什么好股票推荐吗",
        "2026-06-20 11:35:44 [张伟] 最近行情不错，YY股份目标价50，现在才20，翻倍不是问题",
        "2026-06-20 13:00:03 [张伟] 午评：大盘企稳反弹，建议积极做多",
        "2026-06-20 13:15:29 [客户F] 经理，我朋友说有内幕消息，靠谱吗",
        "2026-06-20 13:20:11 [张伟] 小道消息少听，我们做投资要靠基本面分析",
        "2026-06-20 14:00:47 [客户G] 张经理，我亏了50万，要去证监会投诉你们",
        "2026-06-20 14:10:33 [张伟] 请您冷静，有什么问题我们可以协商解决",
        "2026-06-20 14:30:05 [客户H] 我要起诉你们，虚假宣传，赔偿我的损失",
        "2026-06-20 15:00:22 [张伟] 收盘了，今天整体还不错，大家注意控制仓位",
        "2026-06-20 15:15:08 [张伟] 今天的收评稍后发到群里，感谢大家的信任",
    ]
    return lines
