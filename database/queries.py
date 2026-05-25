# database/queries.py
"""
Pure SQLite query helpers for the /profile route.
No Flask imports. Each function opens get_db(), queries, closes, returns.
"""

from database.db import get_db


def _initials(name: str) -> str:
    """Return up to 2 uppercase initials from a full name string."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


def get_user_by_id(user_id: int):
    """
    Return a dict with name, email, member_since, initials for the given
    user_id, or None if the user does not exist.
    member_since is formatted as "Month YYYY" (e.g. "January 2026").
    """
    from datetime import datetime
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    dt = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
        "initials": _initials(row["name"]),
    }


def get_recent_transactions(user_id: int, limit: int = 10):
    """
    Return a list of the most recent `limit` expense dicts for user_id,
    ordered newest-first.
    Each dict has: date (str "Mon DD, YYYY"), description, category, amount (float).
    """
    from datetime import datetime
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount"
        " FROM expenses"
        " WHERE user_id = ?"
        " ORDER BY date DESC, id DESC"
        " LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        dt = datetime.strptime(row["date"], "%Y-%m-%d")
        result.append({
            "date": dt.strftime("%b %d, %Y"),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": row["amount"],   # float — route formats as ₹X.XX
        })
    return result


# ── S2 STUB ───────────────────────────────────────────────────────────────
def get_summary_stats(user_id: int):
    """
    Return a dict with total_spent (float), transaction_count (int),
    top_category (str). Returns zeros/dash if no expenses.
    """
    # S2-STUB-START
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_spent,"
        "       COUNT(*) AS transaction_count"
        " FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?"
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return {
        "total_spent":       row["total_spent"],
        "transaction_count": row["transaction_count"],
        "top_category":      top["category"] if top else "—",
    }
    # S2-STUB-END


# ── S3 STUB ───────────────────────────────────────────────────────────────
def get_category_breakdown(user_id: int):
    """
    Return list of category dicts ordered by amount desc.
    Each dict: name (str), amount (float), pct (int).
    pct values sum to 100. Empty list if no expenses.
    """
    # S3-STUB-START
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS cat_total"
        " FROM expenses"
        " WHERE user_id = ?"
        " GROUP BY category"
        " ORDER BY cat_total DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand_total = sum(r["cat_total"] for r in rows)
    breakdown = [
        {
            "name":   r["category"],
            "amount": r["cat_total"],
            "pct":    int(r["cat_total"] / grand_total * 100),
        }
        for r in rows
    ]
    # Absorb rounding remainder into the largest (first) category
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)
    return breakdown
    # S3-STUB-END
