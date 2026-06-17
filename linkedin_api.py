import os
import requests

# ── How LinkedIn posting works ─────────────────────────────────────────────────
#
# LinkedIn's API uses OAuth 2.0 access tokens.
# We hit the /ugcPosts endpoint with a JSON payload describing the post.
# The "author" field must be your LinkedIn member URN — a unique ID that looks
# like "urn:li:person:XXXXXXXX". You get this from the LinkedIn API or your
# developer dashboard.
#
# Both the access token and URN come from your .env file.

LINKEDIN_API_URL = "https://api.linkedin.com/v2/ugcPosts"


def post_to_linkedin(content: str) -> dict:
    """
    Publish a text post to LinkedIn.
    Returns the full API response dict so the caller can log the post ID.
    Raises an exception if the API returns an error.
    """
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn   = os.getenv("LINKEDIN_PERSON_URN")  # e.g. "urn:li:person:abc123"

    if not access_token or not person_urn:
        raise EnvironmentError(
            "LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN must be set in your .env file."
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # This is the payload shape LinkedIn's UGC Posts API expects.
    # "CONNECTIONS" visibility means only your connections see it.
    # Change to "PUBLIC" when you're ready to post publicly.
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    response = requests.post(LINKEDIN_API_URL, headers=headers, json=payload)

    if not response.ok:
        raise RuntimeError(
            f"LinkedIn API error {response.status_code}: {response.text}"
        )

    return response.json()
