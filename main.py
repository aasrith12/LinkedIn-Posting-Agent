import os
import imaplib
import smtplib
import email as email_lib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from content_brain import generate_linkedin_post
from linkedin_api import post_to_linkedin
from logger import init_db, save_draft, set_status, mark_posted, get_pending_post, get_post_awaiting_approval

load_dotenv()

# ── Two scheduled jobs ─────────────────────────────────────────────────────────
#
# Job 1 — runs at 9:30 PM CST:
#   Generate tomorrow's post, save it to the DB as 'pending', email you a preview.
#
# Job 2 — runs at 9:55 AM CST (5 min before posting):
#   Check your inbox for a reply containing "YES" or "APPROVE".
#   If found → mark the post 'approved'.
#   Then at 10:00 AM the actual post job checks the DB and posts if approved.
#
# Why check at 9:55 and post at 10:00?
#   Separating the inbox-check from the post keeps each function doing one thing.
#   It also gives you a 5-minute buffer if the email check is slow.


# ─── Email helpers ─────────────────────────────────────────────────────────────

def send_preview_email(post_content: str, post_id: int) -> None:
    """Send the post preview to NOTIFY_EMAIL at 9:30 PM."""
    gmail_address   = os.getenv("GMAIL_ADDRESS")
    app_password    = os.getenv("GMAIL_APP_PASSWORD")
    notify_email    = os.getenv("NOTIFY_EMAIL")

    msg = MIMEMultipart()
    msg["From"]    = gmail_address
    msg["To"]      = notify_email
    msg["Subject"] = f"[LinkedIn Agent] Preview for tomorrow — Post #{post_id}"

    body = (
        f"Here's your LinkedIn post scheduled for tomorrow at 10:00 AM CST:\n\n"
        f"{'─' * 60}\n\n"
        f"{post_content}\n\n"
        f"{'─' * 60}\n\n"
        f"Character count: {len(post_content)}\n\n"
        f"Reply to this email with YES to approve, or NO to skip tomorrow's post.\n"
        f"If you don't reply, the post will be skipped automatically."
    )
    msg.attach(MIMEText(body, "plain"))

    # Gmail requires SMTP over SSL on port 465.
    # smtplib.SMTP_SSL opens an encrypted connection from the start.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, notify_email, msg.as_string())

    print(f"[{_now()}] Preview email sent for post #{post_id}.")


def check_inbox_for_approval() -> bool:
    """
    Connect to Gmail via IMAP and look for a reply to today's preview email
    that contains 'YES' or 'APPROVE' (case-insensitive).

    IMAP lets us read emails programmatically — it's the same protocol your
    email client uses. imaplib is built into Python, no install needed.

    Returns True if an approval reply is found, False otherwise.
    """
    gmail_address = os.getenv("GMAIL_ADDRESS")
    app_password  = os.getenv("GMAIL_APP_PASSWORD")
    today_subject = f"Re: [LinkedIn Agent] Preview for tomorrow"

    with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
        mail.login(gmail_address, app_password)
        mail.select("inbox")

        # Search ALL emails (read or unread) with "LinkedIn Agent" in the subject.
        # We drop UNSEEN because the user reads the email before replying,
        # which marks it as read — UNSEEN would miss it.
        _, message_ids = mail.search(None, 'SUBJECT "LinkedIn Agent"')

        for mid in message_ids[0].split():
            _, msg_data = mail.fetch(mid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            # Decode MIME-encoded subject (Gmail encodes non-ASCII chars like —)
            raw_subject = msg.get("Subject", "")
            parts = decode_header(raw_subject)
            subject = "".join(
                part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                for part, enc in parts
            )

            # Only look at replies (subject starts with Re:)
            if not subject.lower().startswith("re:"):
                continue

            # Extract plain-text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            if "YES" in body.upper() or "APPROVE" in body.upper():
                return True

    return False


# ─── Scheduled job functions ───────────────────────────────────────────────────

def job_generate_and_preview() -> None:
    """9:30 PM CST — generate post, save to DB, email you for approval."""
    print(f"[{_now()}] Generating post preview...")
    try:
        content = generate_linkedin_post()
        post_id = save_draft(content)
        send_preview_email(content, post_id)
        print(f"[{_now()}] Post #{post_id} saved as pending. Preview emailed.")
    except Exception as e:
        print(f"[{_now()}] ERROR in preview job: {e}")


def job_check_approval() -> None:
    """9:55 AM CST — check inbox, mark post approved if YES reply found."""
    print(f"[{_now()}] Checking inbox for approval...")
    try:
        approved = check_inbox_for_approval()
        pending  = get_post_awaiting_approval()

        if not pending:
            print(f"[{_now()}] No pending post found. Nothing to approve.")
            return

        if approved:
            set_status(pending["id"], "approved")
            print(f"[{_now()}] Post #{pending['id']} approved. Will post at 10 AM.")
        else:
            set_status(pending["id"], "skipped")
            print(f"[{_now()}] No approval reply found. Post #{pending['id']} will be skipped.")
    except Exception as e:
        print(f"[{_now()}] ERROR in approval check: {e}")


def job_post_to_linkedin() -> None:
    """10:00 AM CST — post to LinkedIn if approved, otherwise skip."""
    print(f"[{_now()}] Running post job...")
    try:
        approved_post = get_pending_post()  # returns only 'approved' status rows

        if not approved_post:
            print(f"[{_now()}] No approved post. Skipping today.")
            return

        post_to_linkedin(approved_post["content"])
        mark_posted(approved_post["id"])
        print(f"[{_now()}] Post #{approved_post['id']} published to LinkedIn.")
    except Exception as e:
        print(f"[{_now()}] ERROR in post job: {e}")


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ─── Scheduler setup ──────────────────────────────────────────────────────────
#
# APScheduler's CronTrigger works like a Unix cron expression.
# CST = UTC-6. So:
#   9:30 PM CST  = 03:30 UTC (next day)
#   9:55 AM CST  = 15:55 UTC
#   10:00 AM CST = 16:00 UTC
#
# BlockingScheduler keeps the script running indefinitely.
# It blocks the main thread, so the script won't exit after setup.

if __name__ == "__main__":
    init_db()  # create posts.db and the table if they don't exist yet

    scheduler = BlockingScheduler(timezone="America/Chicago")  # CST/CDT handled automatically

    scheduler.add_job(
        job_generate_and_preview,
        CronTrigger(hour=21, minute=30, timezone="America/Chicago"),
        id="preview_job",
        name="Generate & email post preview",
    )

    scheduler.add_job(
        job_check_approval,
        CronTrigger(hour=9, minute=55, timezone="America/Chicago"),
        id="approval_check_job",
        name="Check inbox for YES/NO reply",
    )

    scheduler.add_job(
        job_post_to_linkedin,
        CronTrigger(hour=10, minute=0, timezone="America/Chicago"),
        id="post_job",
        name="Post to LinkedIn if approved",
    )

    print(f"[{_now()}] LinkedIn Agent started. Scheduler running...")
    print("  - 9:30 PM CST: generate post + send preview email")
    print("  - 9:55 AM CST: check your inbox for YES/NO reply")
    print("  - 10:00 AM CST: post to LinkedIn if approved")
    print("Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nAgent stopped.")
