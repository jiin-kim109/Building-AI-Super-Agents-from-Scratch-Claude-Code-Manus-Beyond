"""Create the demo analytics warehouse in workspace/warehouse.db."""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "workspace" / "warehouse.db"
DB.parent.mkdir(parents=True, exist_ok=True)
DB.unlink(missing_ok=True)

random.seed(7)
con = sqlite3.connect(DB)

con.executescript(
    """
    CREATE TABLE dim_users (
        user_id INTEGER PRIMARY KEY,
        signed_up_at TEXT,
        plan TEXT,
        is_internal INTEGER
    );
    CREATE TABLE fct_orders (
        order_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        ordered_at TEXT,
        amount_cents INTEGER,
        status TEXT
    );
    CREATE TABLE fct_sessions (
        session_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        started_at TEXT
    );
    """
)

today = datetime.now()


def iso(days_ago: int) -> str:
    return (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")


users = []
for uid in range(1, 421):
    internal = 1 if uid <= 24 else 0
    users.append((uid, iso(random.randint(30, 700)),
                  random.choice(["free", "pro", "team"]), internal))

con.executemany("INSERT INTO dim_users VALUES (?,?,?,?)", users)

sessions = []
sid = 1
for uid, _, _, internal in users:
    # internal accounts are very chatty, which is why they must be excluded
    count = random.randint(4, 18) if internal else random.choices(
        [0, 1, 2, 3, 5, 9], weights=[22, 26, 18, 14, 12, 8]
    )[0]
    for _ in range(count):
        sessions.append((sid, uid, iso(random.randint(0, 27))))
        sid += 1

con.executemany("INSERT INTO fct_sessions VALUES (?,?,?)", sessions)

orders = []
oid = 1
for uid, _, plan, _ in users:
    base = {"free": 0, "pro": 4900, "team": 14900}[plan]
    if base == 0:
        continue
    for _ in range(random.randint(0, 3)):
        orders.append((oid, uid, iso(random.randint(0, 40)), base, "paid"))
        oid += 1

# refunds, recorded as negative rows
for order in random.sample(orders, k=int(len(orders) * 0.05)):
    orders.append((oid, order[1], iso(random.randint(0, 30)), -order[3], "refund"))
    oid += 1

con.executemany("INSERT INTO fct_orders VALUES (?,?,?,?,?)", orders)
con.commit()

active = con.execute(
    """
    SELECT COUNT(*) FROM (
        SELECT s.user_id FROM fct_sessions s
        JOIN dim_users u ON u.user_id = s.user_id
        WHERE u.is_internal = 0
        GROUP BY s.user_id HAVING COUNT(*) >= 2
    )
    """
).fetchone()[0]

revenue = con.execute("SELECT SUM(amount_cents) FROM fct_orders").fetchone()[0]

print(f"seeded {DB}")
print(f"  active users (correct answer) = {active}")
print(f"  revenue (correct answer)      = ${revenue / 100:,.2f}")

con.close()
