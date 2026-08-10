# warehouse
Query the internal analytics warehouse. Read this before writing any revenue or user query.

## Connection

The warehouse is a read-only SQLite file at `warehouse.db` in the working
directory. Query it with Python:

```python
import sqlite3
con = sqlite3.connect("warehouse.db")
```

Never write to it.

## Tables

`fct_orders` — one row per order.
  `order_id`, `user_id`, `ordered_at` (ISO date), `amount_cents`, `status`

  Amounts are stored in **cents**, not dollars. Divide by 100 for display.
  Refunds are recorded as **negative rows** with `status = 'refund'`.
  A revenue query that filters them out will overstate by roughly 4%.

`dim_users` — one row per user.
  `user_id`, `signed_up_at`, `plan`, `is_internal`

  This table includes internal test accounts. Always filter
  `is_internal = 0`, or the numbers will be inflated.

`fct_sessions` — one row per session, not per user.
  `session_id`, `user_id`, `started_at`

## Definitions

An **active user** is a user with 2 or more sessions in the trailing 28 days.
Not 30 days, and not 1 session. Marketing dashboards use a looser definition,
so if our number disagrees with theirs, this is usually why.

**Revenue** is the sum of `amount_cents` across all rows including refunds,
divided by 100.

## Reporting

Report currency as `$1,234.56`. Always state the window you measured.
