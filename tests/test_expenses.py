from datetime import date

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _expense_payload(n=2, auto_categorize=False):
    return {
        "expenses": [
            {
                "raw_text": f"ATB {i * 100} UAH",
                "amount": float(i * 100),
                "currency": "UAH",
                "date": f"2024-0{(i % 2) + 1}-{i + 10}",
                "source": "PrivatBank",
            }
            for i in range(1, n + 1)
        ],
        "auto_categorize": auto_categorize,
    }


# ------------------------------------------------------------------ #
# Health                                                               #
# ------------------------------------------------------------------ #

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


# ------------------------------------------------------------------ #
# Upload                                                               #
# ------------------------------------------------------------------ #

def test_upload_stores_expenses(client):
    r = client.post("/expenses/upload", json=_expense_payload(3))
    assert r.status_code == 201
    body = r.json()
    assert body["stored"] == 3
    assert len(body["expense_ids"]) == 3
    assert body["categorization_status"] == "skipped"


def test_upload_auto_categorize_queues(client):
    payload = _expense_payload(1, auto_categorize=True)
    r = client.post("/expenses/upload", json=payload)
    assert r.status_code == 201
    # categorization is queued (async) - just verify status field
    assert r.json()["categorization_status"] == "queued"


def test_upload_validates_amount(client):
    payload = {
        "expenses": [{"raw_text": "ATB", "amount": -50.0, "currency": "UAH", "date": "2024-01-01"}],
        "auto_categorize": False,
    }
    r = client.post("/expenses/upload", json=payload)
    assert r.status_code == 422


# ------------------------------------------------------------------ #
# List / Filter                                                        #
# ------------------------------------------------------------------ #

def test_list_expenses_returns_all(client):
    client.post("/expenses/upload", json=_expense_payload(5))
    r = client.get("/expenses/")
    assert r.status_code == 200
    assert r.json()["total"] == 5


def test_list_expenses_pagination(client):
    client.post("/expenses/upload", json=_expense_payload(10))
    r = client.get("/expenses/?skip=5&limit=3")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 3


def test_list_filter_is_income(client):
    # Upload mix of expenses and income
    payload = {
        "expenses": [
            {"raw_text": "Salary", "amount": 30000.0, "currency": "UAH", "date": "2024-01-01", "is_income": True},
            {"raw_text": "ATB", "amount": 450.0, "currency": "UAH", "date": "2024-01-02", "is_income": False},
        ],
        "auto_categorize": False,
    }
    client.post("/expenses/upload", json=payload)
    r = client.get("/expenses/?is_income=true")
    items = r.json()["items"]
    assert all(i["is_income"] for i in items)
    assert len(items) == 1


def test_list_status_filter_total_matches_items(client):
    upload = client.post("/expenses/upload", json=_expense_payload(2))
    eids = upload.json()["expense_ids"]
    client.patch(f"/expenses/{eids[0]}", json={"category": "Groceries"})

    r = client.get("/expenses/?status=manual")
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["categorization_status"] == "manual"


def test_list_invalid_month_returns_422(client):
    r = client.get("/expenses/?month=2024-bad")
    assert r.status_code == 422


# ------------------------------------------------------------------ #
# Single expense CRUD                                                  #
# ------------------------------------------------------------------ #

def test_get_expense_by_id(client):
    upload = client.post("/expenses/upload", json=_expense_payload(1))
    eid = upload.json()["expense_ids"][0]
    r = client.get(f"/expenses/{eid}")
    assert r.status_code == 200
    assert r.json()["id"] == eid


def test_get_expense_not_found(client):
    r = client.get("/expenses/99999")
    assert r.status_code == 404


def test_update_category_manual(client):
    upload = client.post("/expenses/upload", json=_expense_payload(1))
    eid = upload.json()["expense_ids"][0]
    r = client.patch(f"/expenses/{eid}", json={"category": "Groceries"})
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == "Groceries"
    assert body["categorization_status"] == "manual"
    assert body["category_confidence"] == 1.0


def test_update_invalid_category(client):
    upload = client.post("/expenses/upload", json=_expense_payload(1))
    eid = upload.json()["expense_ids"][0]
    r = client.patch(f"/expenses/{eid}", json={"category": "NotACategory"})
    assert r.status_code == 422


def test_delete_expense(client):
    upload = client.post("/expenses/upload", json=_expense_payload(1))
    eid = upload.json()["expense_ids"][0]
    r = client.delete(f"/expenses/{eid}")
    assert r.status_code == 204
    r2 = client.get(f"/expenses/{eid}")
    assert r2.status_code == 404


# ------------------------------------------------------------------ #
# Summaries                                                            #
# ------------------------------------------------------------------ #

def test_category_summary_empty(client):
    r = client.get("/expenses/summary/by-category")
    assert r.status_code == 200
    assert r.json() == []


def test_category_summary_with_data(client):
    # Upload and manually categorize
    upload = client.post("/expenses/upload", json=_expense_payload(2))
    eids = upload.json()["expense_ids"]
    client.patch(f"/expenses/{eids[0]}", json={"category": "Groceries"})
    client.patch(f"/expenses/{eids[1]}", json={"category": "Car/Fuel"})

    r = client.get("/expenses/summary/by-category")
    assert r.status_code == 200
    cats = {c["category"] for c in r.json()}
    assert "Groceries" in cats
    assert "Car/Fuel" in cats


def test_monthly_summary_counts_transactions(client):
    upload = client.post("/expenses/upload", json=_expense_payload(2))
    eids = upload.json()["expense_ids"]
    client.patch(f"/expenses/{eids[0]}", json={"category": "Groceries"})
    client.patch(f"/expenses/{eids[1]}", json={"category": "Car/Fuel"})

    r = client.get("/expenses/summary/monthly?month=2024-01")
    assert r.status_code == 200
    body = r.json()
    assert body["transaction_count"] == 1
    assert body["categories"][0]["transaction_count"] == 1


# ------------------------------------------------------------------ #
# Forecast (no data - 422)                                             #
# ------------------------------------------------------------------ #

def test_forecast_no_data(client):
    r = client.get("/forecast/")
    assert r.status_code == 422


def test_model_info_not_trained(client):
    r = client.get("/forecast/model-info")
    assert r.status_code == 200
    body = r.json()
    assert body["ready_for_forecast"] == False
    assert body["status"] == "not_trained"
