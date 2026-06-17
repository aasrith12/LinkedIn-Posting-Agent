import sqlite3
from datetime import datetime, timezone

DB_PATH = "posts.db"

# ── What is SQLite and why use it here? ───────────────────────────────────────
#
# SQLite is a file-based database — no server to run, no setup.
# It stores everything in a single file (posts.db) in your project folder.
# Perfect for a single-user agent like this one.
#
# We have one table: `posts`
# Each row = one day's scheduled post, with columns tracking its full lifecycle:
#   draft → pending approval → approved/skipped → posted/skipped


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name: row["content"]
    return conn


def init_db() -> None:
    """Create the posts table if it doesn't exist yet. Safe to call on every startup."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content     TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending',
                -- status values: 'pending' | 'approved' | 'skipped' | 'posted'
                created_at  TEXT    NOT NULL,
                posted_at   TEXT
            )
        """)


def save_draft(content: str) -> int:
    """Save a newly generated post as 'pending' (awaiting your approval).
    Returns the row id so we can reference this post later."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO posts (content, status, created_at) VALUES (?, ?, ?)",
            (content, "pending", now),
        )
        return cursor.lastrowid


def set_status(post_id: int, status: str) -> None:
    """Update a post's status. Valid values: 'approved', 'skipped', 'posted'."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE posts SET status = ? WHERE id = ?",
            (status, post_id),
        )


def mark_posted(post_id: int) -> None:
    """Mark a post as posted and record the exact timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        conn.execute(
            "UPDATE posts SET status = 'posted', posted_at = ? WHERE id = ?",
            (now, post_id),
        )


def get_post_awaiting_approval() -> dict | None:
    """Return the most recent post with status 'pending' (not yet approved/skipped).
    The 9:55 AM approval-check job calls this."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM posts WHERE status = 'pending' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_pending_post() -> dict | None:
    """Return the most recent post with status 'approved'.
    The 10 AM post job calls this to decide whether to post today."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM posts WHERE status = 'approved' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_recent_posts(limit: int = 10) -> list[dict]:
    """Return the N most recent posts — useful for reviewing history."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
