import anthropic
from dotenv import load_dotenv

load_dotenv()

# ── How this works ─────────────────────────────────────────────────────────────
#
# Instead of fetching RSS feeds ourselves (which failed on Railway due to network
# restrictions), we give Claude a built-in web_search tool.
#
# web_search_20260209 is a SERVER-SIDE tool — Anthropic executes the searches
# on their infrastructure. We just declare it in tools[]. Claude decides when
# to search, runs the searches, reads the results, and writes the post — all
# in a single API call. The only outbound request we make is to Anthropic's API.

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
- NO made-up facts — only use information from verified sources you search
- NO markdown formatting — no **bold**, no *italic*, no headers, no bullet dashes. Plain text only.
- Output the post ONCE, directly. No preamble, no "Here's the post:", no separators, no second version."""

USER_PROMPT = """Search for the most significant AI news story published today or in the last 24 hours.
Look for real, specific, verifiable developments — a model release, a research paper, a major product launch, a policy decision, or a breakthrough.

Write a LinkedIn post that:
1. Opens with a strong hook — a specific fact or observation (NOT a question)
2. Shares 2–3 genuine takeaways or implications in your own words
3. References the source with its full URL somewhere in the body
4. Closes with 3–5 trending hashtags on a new line

Output ONLY the final post text. Nothing before it, nothing after it."""


def generate_linkedin_post() -> str:
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": USER_PROMPT}]

    # Server-side tool — Anthropic runs the searches, not us.
    # Claude may need multiple search rounds; the API handles that loop internally.
    # If stop_reason is "pause_turn" it means the server-side loop hit its limit
    # and we need to re-send to continue.
    for _ in range(3):  # allow up to 3 continuation rounds
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration limit — re-send to continue
            messages = [
                {"role": "user", "content": USER_PROMPT},
                {"role": "assistant", "content": response.content},
            ]
            continue

        break  # any other stop_reason — take what we have

    # Extract the final text block from the response
    for block in reversed(response.content):
        if hasattr(block, "type") and block.type == "text":
            return block.text.strip()

    raise RuntimeError("Claude returned no text content — check API response.")


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Searching for AI news and generating post...\n")
    post = generate_linkedin_post()
    print(post)
    print(f"\n--- Character count: {len(post)} ---")
