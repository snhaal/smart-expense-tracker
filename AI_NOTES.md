# AI Notes

I'm a fresher and this is the first take-home I've done for an actual job
application, so I want to be upfront about exactly how much AI I used
here rather than dress it up. I used Claude for pretty much the entire
first pass of the code. What I brought was the direction, the review, and
the four fixes in section 4 below, which I found by actually reading the
code, not by asking for "more features."

## 1. AI-generated vs. written by me

Claude wrote the first version of everything: `src/main.py`,
`src/models.py`, `src/storage.py`, `tests/test_api.py`, `pytest.ini`,
`requirements.txt`, and the README. I didn't type that code out by hand.

What was mine going in:
- I chose FastAPI. I already know Python better than JS or Java, and
  FastAPI validates requests and generates docs for free, which felt like
  the right trade for a 4-hour budget.
- I chose JSON-file storage since the brief said no database was needed,
  and specifically wanted it to survive a server restart rather than
  living only in memory.
- I picked the monthly-summary bonus over search or Docker because it
  reuses the same grouping/summing logic as the category totals instead
  of adding something unrelated.

Everything past that first version — the four things in section 4 — I
directed myself after actually reading through what Claude gave me.

## 2. What I validated, tested, or changed, and why

- Installed into a completely fresh virtual environment and ran
  `pytest tests/ -v` — the exact commands in the README, in that order —
  to make sure it works the way a reviewer running it cold would
  experience it, not just in whatever environment it was written in.
- Ran the server locally and went through every endpoint by hand with
  `curl` — add, list, filter by category, both total endpoints, delete,
  deleting something that doesn't exist — to check actual response
  bodies and status codes, not just that the automated tests were green.
- Read `storage.py` properly, not skimmed it, and worked out the
  concurrency story myself: the `threading.Lock` stops two requests in
  the *same* process from corrupting the file, but it does nothing if
  you ran this with multiple worker processes at once. That's a real gap
  I can point to, not something I'm repeating from a comment.
- Double-checked the validation rules by actually sending bad input —
  amount of 0, a negative amount, a badly formatted date — and confirmed
  each one comes back as a 422, both in tests and against the live
  server.

## 3. AI suggestions I looked at and didn't change, and why

- **Amounts stored as `float`.** This is a genuinely known problem for
  money — floats don't represent something like 0.1 exactly, so totals
  can drift by fractions of a cent over enough additions. I left it as
  is because this project's scope doesn't involve enough volume for that
  to actually show up, but I know the fix (`Decimal`, or storing cents as
  integers) and would do it if this were a real product.
- **Auto-incrementing integer IDs instead of UUIDs.** Simple, reads
  cleanly in a JSON file, but it tells anyone looking how many expenses
  exist, and it isn't safe with multiple writers. I kept it because this
  has a single writer and I valued the readability, but I wouldn't
  defend it as the objectively correct choice.
- **JSON file instead of SQLite.** The obvious "more correct" option is
  SQLite — real transactions, no manual file locking. I didn't switch
  because the brief said no database was required, but if I extended
  this, this is the first thing I'd change. The storage layer is wired
  through FastAPI's dependency injection (`Depends(get_storage)`)
  specifically so that swap wouldn't touch the route code at all.

## 4. What I changed myself after reading through the first version

After going through the code properly (not just running it), I found four
things worth fixing and had Claude implement them. I tested every one of
these myself before deciding they were good enough to keep:

**Future-dated expenses were accepted.** The date field only checked
formatting, not whether the date made sense — you could log an expense
for the year 2099 and it would go straight into your totals. Added a
check that rejects any date later than today.

**Category matching was actually inconsistent, not just a style choice.**
This is the one I'm most glad I caught. `GET /expenses?category=food`
matched case-insensitively, but the totals-by-category breakdown grouped
by the exact string — so if you added expenses under `"Food"` and
`"food"`, the filter would treat them as the same category but the totals
breakdown would silently split them into two. I normalized category
casing at write time so both parts of the code agree with each other.

**There was no way to fetch a single expense.** Only add, list, and
delete existed. Added `GET /expenses/{id}`. The part I actually had to
think about: it has to be declared *after* the other `/expenses/...`
routes in `main.py`, because FastAPI matches routes in the order they're
written, and if the id route came first, a request to `/expenses/total`
would try to parse "total" as an integer id and break. I added a test
specifically for this so it can't quietly regress later if someone
reorders the routes.

**Writes to the JSON file weren't crash-safe.** If the process died in
the middle of writing `data.json`, you could be left with a half-written,
unreadable file. Changed it to write to a temp file first and swap it in
with `os.replace()`, which is atomic — so the file on disk is always
either fully the old version or fully the new one. Worth being honest
that this doesn't fix everything: it only protects against one write
being interrupted, not two processes writing to the file at the same
time — that's still the same concurrency limitation from section 2.

All four are covered by new tests. Full suite is 21 tests, all passing,
run from a clean checkout.
