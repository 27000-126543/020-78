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
        self.groups = []
        self._next_group_id = 1

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
                "history": [],
                "group_id": None,
            }
            self.items.append(item)
            self._next_id += 1
            added += 1
        return added

    def add_chat_risks(self, chat_data, department=None):
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
                "department": department if department else "-",
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
                "history": [],
                "group_id": None,
            }
            self.items.append(item)
            self._next_id += 1
            added += 1
        return added

    def update_status(self, item_id, new_status, note=None, reviewer=None):
        if new_status not in ALL_STATUSES:
            return False
        for item in self.items:
            if item["id"] == item_id:
                item["status"] = new_status
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                action = {
                    "time": item["updated_at"],
                    "action_type": new_status,
                    "note": note or "",
                    "reviewer": reviewer or "",
                }
                if "history" not in item:
                    item["history"] = []
                item["history"].append(action)
                return True
        return False

    def bulk_update_status(self, item_ids, new_status, note=None, reviewer=None):
        if new_status not in ALL_STATUSES:
            return 0
        updated = 0
        for item in self.items:
            if item["id"] in item_ids:
                item["status"] = new_status
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                action = {
                    "time": item["updated_at"],
                    "action_type": new_status,
                    "note": note or "",
                    "reviewer": reviewer or "",
                }
                if "history" not in item:
                    item["history"] = []
                item["history"].append(action)
                updated += 1
        return updated

    def append_action(self, item_id, action_type, note=None, reviewer=None):
        valid_actions = ALL_STATUSES + ["追加备注", "合规复核"]
        if action_type not in valid_actions:
            return False
        for item in self.items:
            if item["id"] == item_id:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                action = {
                    "time": now,
                    "action_type": action_type,
                    "note": note or "",
                    "reviewer": reviewer or "",
                }
                if "history" not in item:
                    item["history"] = []
                item["history"].append(action)
                item["updated_at"] = now
                if action_type in ALL_STATUSES:
                    item["status"] = action_type
                return True
        return False

    def get_last_action(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                history = item.get("history", [])
                if not history:
                    return None
                return history[-1]
        return None

    def add_propagation_group(self, duplicate_item, department=None):
        content = duplicate_item["content"].strip()
        file_names = duplicate_item.get("files", [])
        speakers = duplicate_item.get("speakers", [])
        categories = duplicate_item.get("categories", [])

        member_ids = []
        for item in self.items:
            if item.get("content", "").strip() == content and item.get("source") == "群聊":
                if item.get("source_detail", "") in file_names:
                    member_ids.append(item["id"])

        group = {
            "id": self._next_group_id,
            "content": content,
            "file_count": duplicate_item.get("file_count", len(file_names)),
            "repeat_count": duplicate_item.get("count", len(member_ids)),
            "files": file_names,
            "speakers": speakers,
            "categories": categories,
            "department": department if department else "-",
            "member_ids": member_ids,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.groups.append(group)
        gid = self._next_group_id
        for mid in member_ids:
            for item in self.items:
                if item["id"] == mid:
                    item["group_id"] = gid
        self._next_group_id += 1
        return gid

    def get_propagation_groups(self, department=None):
        groups = self.groups[:]
        if department:
            groups = [g for g in groups if department.lower() in g.get("department", "").lower()]
        return groups

    def get_group_summary(self, group_id):
        group = None
        for g in self.groups:
            if g["id"] == group_id:
                group = g
                break
        if not group:
            return None
        members = [i for i in self.items if i.get("group_id") == group_id]
        status_dist = {}
        for m in members:
            s = m.get("status", STATUS_PENDING)
            status_dist[s] = status_dist.get(s, 0) + 1
        return {
            "group": group,
            "members": members,
            "status_distribution": status_dist,
        }

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
                    "groups": self.groups,
                    "next_group_id": self._next_group_id,
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
            self.groups = data.get("groups", [])
            self._next_group_id = data.get("next_group_id", len(self.groups) + 1)
            for item in self.items:
                if "history" not in item:
                    item["history"] = []
                if "group_id" not in item:
                    item["group_id"] = None
            return True
        except Exception:
            return False

    def get_closure_view(self, days=7):
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        recent = [i for i in self.items if i.get("added_at", "") >= cutoff_str]
        counts = {"新增": 0, STATUS_PENDING: 0, STATUS_REMINDED: 0, STATUS_RECTIFIED: 0}
        counts["新增"] = len(recent)
        for item in recent:
            s = item.get("status", STATUS_PENDING)
            if s in counts:
                counts[s] += 1
        return {
            "days": days,
            "total_added": counts["新增"],
            "pending": counts[STATUS_PENDING],
            "reminded": counts[STATUS_REMINDED],
            "rectified": counts[STATUS_RECTIFIED],
            "items": recent,
        }

    def get_overdue_items(self, overdue_days=3):
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=overdue_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        overdue = []
        for item in self.items:
            status = item.get("status", STATUS_PENDING)
            if status in [STATUS_PENDING, STATUS_REMINDED]:
                added = item.get("added_at", "")
                if added and added < cutoff_str:
                    overdue.append(item)
        return overdue

    def get_pending_summary(self):
        pending = [i for i in self.items if i.get("status") == STATUS_PENDING]
        reminded = [i for i in self.items if i.get("status") == STATUS_REMINDED]
        dept_dist = {}
        mgr_dist = {}
        for item in pending + reminded:
            d = item.get("department", "-")
            dept_dist[d] = dept_dist.get(d, 0) + 1
            m = item.get("manager", "-")
            mgr_dist[m] = mgr_dist.get(m, 0) + 1
        return {
            "pending_count": len(pending),
            "reminded_count": len(reminded),
            "by_department": dept_dist,
            "by_manager": mgr_dist,
        }
