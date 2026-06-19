import json
import os
from datetime import datetime


STATUS_PENDING = "待核实"
STATUS_REMINDED = "已提醒"
STATUS_RECTIFIED = "已整改"

ALL_STATUSES = [STATUS_PENDING, STATUS_REMINDED, STATUS_RECTIFIED]


class RiskLedger:
    def __init__(self):
        self.items = []
        self._next_id = 1

    def add_rumor_risks(self, rumor_data):
        if not rumor_data or not rumor_data.get("performed"):
            return 0
        results = rumor_data.get("results", [])
        added = 0
        for r in results:
            item = {
                "id": self._next_id,
                "source": "舆情",
                "department": r.get("department", "-"),
                "manager": r.get("manager", "-"),
                "source_detail": r.get("source", "-"),
                "content": r.get("content", ""),
                "risk_level": r.get("highest_risk", "medium"),
                "risk_categories": r.get("risk_categories", []),
                "stock": r.get("stock", ""),
                "time": r.get("time").strftime("%Y-%m-%d %H:%M") if r.get("time") else "-",
                "status": STATUS_PENDING,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.items.append(item)
            self._next_id += 1
            added += 1
        return added

    def add_chat_risks(self, chat_data):
        if not chat_data or not chat_data.get("performed"):
            return 0

        violations = []
        if chat_data.get("mode") == "folder":
            agg = chat_data.get("aggregate")
            if agg and agg.get("violations"):
                violations = agg["violations"]
        else:
            violations = chat_data.get("violations", [])

        added = 0
        for v in violations:
            item = {
                "id": self._next_id,
                "source": "群聊",
                "department": "-",
                "manager": v.get("speaker", "-"),
                "source_detail": v.get("file_name", "-"),
                "content": v.get("content", ""),
                "risk_level": v.get("highest_risk", "medium"),
                "risk_categories": [m["category"] for m in v.get("sensitive_matches", [])],
                "stock": "",
                "time": v.get("timestamp", "-"),
                "line_number": v.get("line_number", 0),
                "status": STATUS_PENDING,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.items.append(item)
            self._next_id += 1
            added += 1
        return added

    def update_status(self, item_id, new_status):
        if new_status not in ALL_STATUSES:
            return False
        for item in self.items:
            if item["id"] == item_id:
                item["status"] = new_status
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True
        return False

    def bulk_update_status(self, item_ids, new_status):
        if new_status not in ALL_STATUSES:
            return 0
        updated = 0
        for item in self.items:
            if item["id"] in item_ids:
                item["status"] = new_status
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated += 1
        return updated

    def filter_items(self, department=None, manager=None, risk_type=None, status=None):
        filtered = self.items[:]
        if department:
            filtered = [i for i in filtered if department.lower() in i.get("department", "").lower()]
        if manager:
            filtered = [i for i in filtered if manager.lower() in i.get("manager", "").lower()]
        if risk_type:
            filtered = [i for i in filtered if risk_type in i.get("risk_categories", [])]
        if status:
            filtered = [i for i in filtered if status == i.get("status")]
        return filtered

    def get_status_summary(self):
        summary = {s: 0 for s in ALL_STATUSES}
        for item in self.items:
            s = item.get("status", STATUS_PENDING)
            if s in summary:
                summary[s] += 1
        return summary

    def get_departments(self):
        return sorted({i["department"] for i in self.items if i.get("department") and i["department"] != "-"})

    def get_managers(self):
        return sorted({i["manager"] for i in self.items if i.get("manager") and i["manager"] != "-"})

    def get_risk_categories(self):
        cats = set()
        for i in self.items:
            for c in i.get("risk_categories", []):
                cats.add(c)
        return sorted(cats)

    def save_to_file(self, filepath):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "items": self.items,
                    "next_id": self._next_id,
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_from_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.items = data.get("items", [])
            self._next_id = data.get("next_id", len(self.items) + 1)
            return True
        except Exception:
            return False
