"""Simple JSON-file backed storage for expenses.

Kept intentionally simple (no ORM, no database) since the assignment scope
is a small take-home API. The file is read/written on every operation so
there's a single source of truth on disk and no in-memory/disk drift.
"""

import json
import os
import threading
from typing import Dict, List, Optional


class ExpenseStorage:
    def __init__(self, filepath: str = "data.json"):
        self.filepath = filepath
        self._lock = threading.Lock()
        if not os.path.exists(self.filepath):
            self._write({"next_id": 1, "expenses": []})

    def _read(self) -> Dict:
        with open(self.filepath, "r") as f:
            return json.load(f)

    def _write(self, data: Dict) -> None:
        # Write to a temp file first, then atomically replace the real file.
        # If the process dies mid-write, data.json is never left half-written —
        # the reader always sees either the old complete file or the new one.
        tmp_path = f"{self.filepath}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.filepath)

    def add_expense(self, title: str, amount: float, category: str, date: str) -> Dict:
        with self._lock:
            data = self._read()
            expense = {
                "id": data["next_id"],
                "title": title,
                "amount": amount,
                # Normalize casing so "food" and "Food" are stored as the same
                # category. Without this, GET /expenses?category=food matches
                # both (case-insensitive filter) but totals-by-category would
                # have split them into two separate entries.
                "category": category.strip().title(),
                "date": date,
            }
            data["expenses"].append(expense)
            data["next_id"] += 1
            self._write(data)
            return expense

    def get_all(self, category: Optional[str] = None) -> List[Dict]:
        expenses = self._read()["expenses"]
        if category:
            expenses = [e for e in expenses if e["category"].lower() == category.lower()]
        return expenses

    def get_by_id(self, expense_id: int) -> Optional[Dict]:
        for e in self._read()["expenses"]:
            if e["id"] == expense_id:
                return e
        return None

    def delete_expense(self, expense_id: int) -> bool:
        with self._lock:
            data = self._read()
            remaining = [e for e in data["expenses"] if e["id"] != expense_id]
            deleted = len(remaining) != len(data["expenses"])
            if deleted:
                data["expenses"] = remaining
                self._write(data)
            return deleted

    def total(self, category: Optional[str] = None) -> float:
        return round(sum(e["amount"] for e in self.get_all(category)), 2)

    def totals_by_category(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for e in self._read()["expenses"]:
            totals[e["category"]] = round(totals.get(e["category"], 0) + e["amount"], 2)
        return totals

    def monthly_summary(self) -> Dict[str, float]:
        """Bonus feature: total spend per calendar month (YYYY-MM)."""
        totals: Dict[str, float] = {}
        for e in self._read()["expenses"]:
            month_key = e["date"][:7]
            totals[month_key] = round(totals.get(month_key, 0) + e["amount"], 2)
        return totals
