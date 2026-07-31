# Smart Expense Tracker API

A REST API for managing personal expenses: add, list, filter by category,
compute totals (overall and per category), and delete. Built with
**FastAPI** and persisted to a local JSON file (`data.json`) — no database
required.

Built for the Software Engineering Apprenticeship take-home. See
`AI_NOTES.md` for how AI tools were used in building this.

## What's included

- `POST /expenses` — add an expense (`title`, `amount`, `category`, `date`). The `id` is assigned by the server.
- `GET /expenses` — list all expenses. Optional `?category=` query param to filter.
- `GET /expenses/total` — total of all expenses. Optional `?category=` to total just one category.
- `GET /expenses/totals-by-category` — a breakdown of totals per category.
- `GET /expenses/{id}` — fetch a single expense by id (404 if it doesn't exist).
- `DELETE /expenses/{id}` — delete an expense by id (404 if it doesn't exist).
- **Bonus:** `GET /expenses/monthly-summary` — total spend grouped by calendar month (`YYYY-MM`).
- **Bonus:** interactive OpenAPI/Swagger docs, generated automatically by FastAPI at `/docs` (and the raw schema at `/openapi.json`).

## Requirements

- Python 3.10+

## Install

```bash
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The API is now available at `http://localhost:8000`. Interactive docs are at
`http://localhost:8000/docs`.

### Example requests

```bash
curl -X POST http://localhost:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"title":"Coffee","amount":4.5,"category":"Food","date":"2026-07-01"}'

curl "http://localhost:8000/expenses?category=Food"

curl http://localhost:8000/expenses/total

curl -X DELETE http://localhost:8000/expenses/1
```

## Run the tests

```bash
pytest tests/ -v
```

Tests use `fastapi.testclient.TestClient` and override the storage
dependency with a temporary JSON file per test, so they never touch the
real `data.json` and each test starts from a clean, empty state.

## Design notes

- **Storage**: a small `ExpenseStorage` class in `src/storage.py` reads/writes
  a JSON file on every operation. Simple and sufficient for this scope;
  no ORM or database.
- **Validation**: Pydantic enforces `amount > 0`, a strict `YYYY-MM-DD`
  date format, and rejects future-dated expenses, returning `422` on bad
  input.
- **Category normalization**: categories are normalized to a canonical
  casing (`.strip().title()`) on write, so `"food"` and `"Food"` are
  treated as one category everywhere — both in filtering and in the
  totals-by-category breakdown.
- **Atomic writes**: `data.json` is written via a temp-file-then-replace
  pattern, so a crash mid-write can't leave a corrupted, half-written
  file behind.
- **Testability**: the storage instance is provided via FastAPI's
  dependency-injection (`Depends(get_storage)`), so tests can swap in an
  isolated instance instead of mutating global state.

## Project structure

```
your-repo/
  README.md
  AI_NOTES.md
  requirements.txt
  pytest.ini
  src/
    __init__.py
    main.py       # FastAPI app and routes
    models.py     # Pydantic request/response models
    storage.py     # JSON-file backed storage
  tests/
    test_api.py   # full endpoint + validation test suite
```
