from .sensitive_words import SENSITIVE_PATTERNS
from .sample_data import generate_sample_rumors, DEPARTMENTS


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


def check_rumors(keyword=None, use_sample=True):
    if use_sample:
        rumors = generate_sample_rumors(keyword)
    else:
        rumors = []

    results = []
    for rumor in rumors:
        sensitive_matches = detect_sensitive_content(rumor["content"])
        if sensitive_matches:
            rumor_copy = rumor.copy()
            rumor_copy["sensitive_matches"] = sensitive_matches
            highest_risk = min(
                sensitive_matches,
                key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["risk_level"]]
            )
            rumor_copy["highest_risk"] = highest_risk["risk_level"]
            rumor_copy["risk_categories"] = [m["category"] for m in sensitive_matches]
            results.append(rumor_copy)

    results.sort(
        key=lambda x: (-x["time"].timestamp(),)
    )

    return {
        "performed": True,
        "keyword": keyword,
        "results": results,
    }


def summarize_rumors_by_scope(rumor_data):
    if not rumor_data or not rumor_data.get("performed"):
        return None

    results = rumor_data["results"]
    if not results:
        return {"dept_count": 0, "manager_count": 0, "stock_count": 0, "groups": set()}

    departments = set()
    managers = set()
    stocks = set()
    groups = set()

    for r in results:
        if r.get("department"):
            departments.add(r["department"])
        if r.get("manager"):
            managers.add(r["manager"])
        if r.get("stock"):
            stocks.add(r["stock"])
        if r.get("source"):
            groups.add(r["source"])

    return {
        "dept_count": len(departments),
        "departments": sorted(departments),
        "manager_count": len(managers),
        "managers": sorted(managers),
        "stock_count": len(stocks),
        "stocks": sorted(stocks),
        "group_count": len(groups),
        "groups": sorted(groups),
    }


def list_departments():
    return list(DEPARTMENTS.keys())
