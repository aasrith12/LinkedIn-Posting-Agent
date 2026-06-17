import feedparser
import anthropic
from dotenv import load_dotenv
from topics import RSS_FEEDS

load_dotenv()

# ── Step 1: Pull fresh articles from RSS feeds ─────────────────────────────────
#
# feedparser.parse() downloads and parses an RSS/Atom feed.
# Each feed has a list called `entries` — those are the individual articles.
# We grab the 2 newest from each feed, trim the summary so we don't blow up
# Claude's context window, and collect them all into one list.

def fetch_recent_ai_news(articles_per_feed: int = 2) -> list[dict]:
    articles = []

    for url in RSS_FEEDS:
        try:
            # agent= sets the HTTP User-Agent; request_headers adds a timeout via urllib
            feed = feedparser.parse(url, agent="LinkedInAgent/1.0", request_headers={"Connection": "close"})

            if feed.bozo and not feed.entries:
                # bozo=True means feedparser hit a parse error and got nothing useful
                print(f"Skipping feed (parse error): {url}")
                continue

            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:articles_per_feed]:
                articles.append({
                    "title":   entry.get("title", "").strip(),
                    "summary": entry.get("summary", "")[:600].strip(),
                    "link":    entry.get("link", ""),
                    "source":  source_name,
                })
        except Exception as e:
            # One bad feed should never stop the whole job
            print(f"Skipping feed {url}: {e}")
            continue

    return articles


# ── Step 2: Format the articles into a compact block of text for Claude ────────
#
# Claude will read this block and decide which story is the most interesting.
# Numbered so Claude can reference them easily.

def _format_articles_for_prompt(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, start=1):
        lines.append(
            f"[{i}] {a['title']}\n"
            f"    Source : {a['source']}\n"
            f"    URL    : {a['link']}\n"
            f"    Excerpt: {a['summary']}\n"
        )
    return "\n".join(lines)


# ── Step 3: Ask Claude to pick the best story and write the LinkedIn post ──────
#
# Two key ideas here:
#
#   system prompt  — sets Claude's permanent persona and hard rules (guardrails).
#                    Think of it as the job description that never changes.
#
#   user prompt    — the actual task for today: "here are the articles, write a post."
#
# We pass the news articles in the user prompt so Claude works only with
# verified, cited sources — it can't make things up if we anchor it to real URLs.

SYSTEM_PROMPT = """You are a professional AI engineer writing daily LinkedIn posts about the latest AI developments worldwide.

PERSONA:
- Thoughtful, curious, and credible — you share genuine insights, not hype
- First person ("I think", "This caught my attention", "What I found interesting...")
- You cite your sources — readers should be able to verify everything you say

HARD RULES (non-negotiable, every single post):
- Under 3000 characters total (including hashtags)
- End with exactly 3 to 5 relevant, trending hashtags on the last line
- Include at least one source URL inline in the post body
- NO profanity or crude language of any kind
- NO NSFW content whatsoever
- NO sensational, clickbait, or fear-mongering language
- NO made-up facts — only use information from the articles provided to you
- Do NOT add any commentary outside the post itself (no "Here's the post:" preamble)"""

USER_PROMPT_TEMPLATE = """Here are today's latest AI news articles:

{news_block}

Pick the single most insightful or impactful story and write a LinkedIn post that:
1. Opens with a strong hook — an observation or a specific fact (NOT a question)
2. Shares 2–3 genuine takeaways or implications in your own words
3. References the source with its full URL somewhere in the body
4. Closes with 3–5 trending hashtags on a new line

Return ONLY the post text. No preamble, no labels, no explanation."""


def generate_linkedin_post() -> str:
    articles = fetch_recent_ai_news()

    if not articles:
        raise RuntimeError("No articles fetched — check your internet connection or RSS feed URLs.")

    news_block = _format_articles_for_prompt(articles)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment automatically

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(news_block=news_block)}
        ],
    )

    post_text = response.content[0].text.strip()
    return post_text


# ── Quick test: run this file directly to see a generated post ─────────────────
if __name__ == "__main__":
    print("Fetching news and generating post...\n")
    post = generate_linkedin_post()
    print(post)
    print(f"\n--- Character count: {len(post)} ---")
