import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.main import app, get_storage
from src.storage import ExpenseStorage


@pytest.fixture
def client():
    """Fresh, isolated storage (a temp JSON file) for every test."""
    tmp_dir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmp_dir, "test_data.json")
    test_storage = ExpenseStorage(tmp_file)
    app.dependency_overrides[get_storage] = lambda: test_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _add(client, title="Coffee", amount=4.5, category="Food", date="2026-07-01"):
    return client.post(
        "/expenses",
        json={"title": title, "amount": amount, "category": category, "date": date},
    )


def test_add_expense_returns_created_record_with_id(client):
    resp = _add(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["title"] == "Coffee"
    assert body["amount"] == 4.5


def test_ids_increment_across_multiple_adds(client):
    first = _add(client, title="Coffee").json()
    second = _add(client, title="Bus").json()
    assert first["id"] == 1
    assert second["id"] == 2


def test_list_expenses_empty_initially(client):
    resp = client.get("/expenses")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_expenses_after_adding(client):
    _add(client)
    resp = client.get("/expenses")
    assert len(resp.json()) == 1


def test_filter_by_category_is_case_insensitive(client):
    _add(client, title="Coffee", category="Food")
    _add(client, title="Bus", category="Travel")
    resp = client.get("/expenses", params={"category": "food"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Coffee"


def test_filter_by_unknown_category_returns_empty(client):
    _add(client, category="Food")
    resp = client.get("/expenses", params={"category": "Nonexistent"})
    assert resp.json() == []


def test_total_overall(client):
    _add(client, amount=4.5, category="Food")
    _add(client, amount=2.0, category="Travel")
    resp = client.get("/expenses/total")
    assert resp.json()["total"] == 6.5


def test_total_by_category(client):
    _add(client, title="Coffee", amount=4.5, category="Food")
    _add(client, title="Lunch", amount=10.0, category="Food")
    _add(client, title="Bus", amount=2.0, category="Travel")
    resp = client.get("/expenses/total", params={"category": "Food"})
    assert resp.json()["total"] == 14.5


def test_totals_by_category_breakdown(client):
    _add(client, amount=4.5, category="Food")
    _add(client, amount=10.0, category="Food")
    _add(client, amount=2.0, category="Travel")
    resp = client.get("/expenses/totals-by-category")
    data = resp.json()
    assert data["Food"] == 14.5
    assert data["Travel"] == 2.0


def test_monthly_summary(client):
    _add(client, amount=4.5, date="2026-06-01")
    _add(client, amount=500, date="2026-07-01")
    _add(client, amount=5.5, date="2026-07-15")
    resp = client.get("/expenses/monthly-summary")
    data = resp.json()
    assert data["2026-06"] == 4.5
    assert data["2026-07"] == 505.5


def test_delete_expense_removes_it(client):
    created = _add(client).json()
    del_resp = client.delete(f"/expenses/{created['id']}")
    assert del_resp.status_code == 204
    assert client.get("/expenses").json() == []


def test_delete_nonexistent_expense_returns_404(client):
    resp = client.delete("/expenses/999")
    assert resp.status_code == 404


def test_invalid_date_format_rejected(client):
    resp = _add(client, date="01-07-2026")
    assert resp.status_code == 422


def test_negative_amount_rejected(client):
    resp = _add(client, amount=-5)
    assert resp.status_code == 422


def test_zero_amount_rejected(client):
    resp = _add(client, amount=0)
    assert resp.status_code == 422


def test_missing_required_field_rejected(client):
    resp = client.post("/expenses", json={"title": "Coffee", "amount": 4.5, "category": "Food"})
    assert resp.status_code == 422


def test_future_dated_expense_rejected(client):
    resp = _add(client, date="2099-01-01")
    assert resp.status_code == 422


def test_category_casing_is_normalized_on_write(client):
    _add(client, title="Coffee", category="food")
    _add(client, title="Lunch", category="Food")
    _add(client, title="Snacks", category="FOOD")
    # all three should have collapsed into a single canonical category
    resp = client.get("/expenses/totals-by-category")
    data = resp.json()
    assert data == {"Food": 4.5 + 4.5 + 4.5}
    # and the filter should only see one category, matching totals-by-category
    resp = client.get("/expenses", params={"category": "food"})
    assert len(resp.json()) == 3


def test_get_single_expense_by_id(client):
    created = _add(client, title="Coffee").json()
    resp = client.get(f"/expenses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Coffee"


def test_get_single_expense_not_found(client):
    resp = client.get("/expenses/999")
    assert resp.status_code == 404


def test_get_by_id_does_not_shadow_total_route(client):
    """Regression test: /expenses/total must never be swallowed by
    /expenses/{expense_id} due to route declaration order."""
    _add(client, amount=4.5)
    resp = client.get("/expenses/total")
    assert resp.status_code == 200
    assert resp.json()["total"] == 4.5
