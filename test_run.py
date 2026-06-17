"""
Manual end-to-end test. Run each step one at a time:
  python test_run.py preview    -- generates post, saves to DB, emails you preview
  python test_run.py check      -- checks inbox for your YES reply, marks approved
  python test_run.py post       -- posts to LinkedIn if approved
"""
import sys
from dotenv import load_dotenv
load_dotenv()

from logger import init_db
init_db()

if len(sys.argv) < 2:
    print("Usage: python test_run.py [preview | check | post]")
    sys.exit(1)

step = sys.argv[1]

if step == "preview":
    from main import job_generate_and_preview
    job_generate_and_preview()

elif step == "check":
    from main import job_check_approval
    job_check_approval()

elif step == "post":
    from main import job_post_to_linkedin
    job_post_to_linkedin()

else:
    print(f"Unknown step '{step}'. Use: preview | check | post")
