# LinkedIn Auto-Post Agent

An autonomous agent that posts insightful AI engineering content to your LinkedIn every day — powered by Claude Sonnet 4.6, live RSS news feeds, and a human-in-the-loop approval step over email.

---

## How It Works

```
9:30 PM CST  →  Fetch AI news → Claude writes post → Email you a preview
      ↓
  You reply YES or NO
      ↓
9:55 AM CST  →  Agent reads your reply from Gmail
10:00 AM CST →  Posts to LinkedIn if approved, skips if not
```

Every post is grounded in real, cited sources from the day's AI news. You approve every post before it goes live. The agent never posts without your explicit sign-off.

---

## Features

- **Live AI news** — pulls from 9 RSS feeds (TechCrunch, VentureBeat, OpenAI, Google AI, HuggingFace, DeepMind, and more)
- **Claude Sonnet 4.6** — picks the most impactful story and writes a professional, first-person post with cited sources and trending hashtags
- **Human approval loop** — preview email at 9:30 PM CST, reply YES to approve or NO to skip
- **Guardrails** — no NSFW, no profanity, no clickbait, no made-up facts — enforced via system prompt on every generation
- **Post rules** — under 3000 characters, first person, ends with 3–5 relevant hashtags
- **Full audit trail** — every post saved to SQLite with status (`pending → approved/skipped → posted`) and timestamps

---

## Project Structure

```
linkedin-agent/
├── main.py           # APScheduler — 3 cron jobs (preview, approval check, post)
├── content_brain.py  # Fetches RSS feeds + calls Claude to generate the post
├── linkedin_api.py   # Posts to LinkedIn via UGC Posts API
├── logger.py         # SQLite wrapper — tracks full post lifecycle
├── topics.py         # Curated list of AI news RSS feed URLs
├── flowchart.html    # Interactive flow chart of the full agent
├── test_run.py       # Manual trigger for each job (for testing)
├── requirements.txt
└── .env              # API keys (never committed)
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| AI / Content | Anthropic API — `claude-sonnet-4-6` |
| Scheduler | APScheduler `BlockingScheduler` |
| News source | RSS feeds via `feedparser` |
| Social posting | LinkedIn UGC Posts API |
| Approval flow | Gmail SMTP (send) + Gmail IMAP (read reply) |
| Storage | SQLite via `sqlite3` (built-in) |
| Config | `python-dotenv` |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/aasrith12/LinkedIn-Posting-Agent.git
cd LinkedIn-Posting-Agent
pip install -r requirements.txt
```

### 2. Create your `.env` file

```env
# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# LinkedIn
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_PERSON_URN=urn:li:person:your_member_id

# Gmail
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
NOTIFY_EMAIL=where_to_send_preview@gmail.com
```

> **Gmail App Password** — not your regular password. Go to Google Account → Security → 2-Step Verification → App Passwords → create one called "LinkedIn Agent".

> **LinkedIn tokens** — create an app at [linkedin.com/developers](https://linkedin.com/developers), add the "Share on LinkedIn" product, and generate an OAuth token with `openid`, `profile`, and `w_member_social` scopes.

### 3. Run

```bash
python main.py
```

The scheduler starts and waits. Nothing posts immediately.

---

## Testing Each Step Manually

```bash
# Step 1 — Generate a post and send you the preview email
python test_run.py preview

# Step 2 — Check your inbox for a YES reply and mark approved
python test_run.py check

# Step 3 — Post to LinkedIn if approved
python test_run.py post
```

---

## Approval Flow

At **9:30 PM CST** you receive an email like this:

```
Subject: [LinkedIn Agent] Preview for tomorrow — Post #12

Here's your LinkedIn post scheduled for tomorrow at 10:00 AM CST:

────────────────────────────────────────────────────────────

Google just retired a 25-year-old interface — and it signals
something much bigger than a visual refresh...

[full post content]

────────────────────────────────────────────────────────────

Reply to this email with YES to approve, or NO to skip.
If you don't reply, the post will be skipped automatically.
```

Reply **YES** → post goes live at 10 AM.
Reply **NO** (or don't reply) → that day is skipped.

---

## Post Guardrails

These are enforced on every single generation via Claude's system prompt:

- No NSFW content
- No profanity or crude language
- No sensational or fear-mongering language
- No made-up facts — only information from the provided news articles
- Must include at least one cited source URL
- Must be under 3000 characters
- Must end with 3–5 relevant hashtags
- Written in first person

---

## Interactive Flow Chart

Open `flowchart.html` in your browser for a full visual map of the agent with hover tooltips on every node showing the exact function, API, or SQL query behind it.

---

## Deployment

This agent is designed to run on a cloud server (Railway, DigitalOcean, etc.) so it stays alive 24/7 without needing your PC on.

Set all `.env` variables as environment variables in your cloud provider's dashboard and set the start command to:

```
python main.py
```
