import os
from flask import Flask
from logger import init_db, get_recent_posts

app = Flask(__name__)

STATUS_BADGE = {
    "pending":  ("#f0883e", "#3d2000", "⏳ Pending"),
    "approved": ("#79c0ff", "#1f3e6b", "✅ Approved"),
    "posted":   ("#56d364", "#1a3a2a", "🚀 Posted"),
    "skipped":  ("#8b949e", "#21262d", "⏭ Skipped"),
}

@app.route("/")
def index():
    init_db()
    posts = get_recent_posts(limit=30)

    rows = ""
    for p in posts:
        color, bg, label = STATUS_BADGE.get(p["status"], ("#e6edf3", "#161b22", p["status"]))

        # Format date nicely
        date_str = p["created_at"][:10] if p["created_at"] else "—"
        posted_str = p["posted_at"][:16].replace("T", " ") + " UTC" if p["posted_at"] else "—"

        # Preview = first 120 chars
        preview = p["content"][:120].replace("<", "&lt;").replace(">", "&gt;")
        if len(p["content"]) > 120:
            preview += "…"

        # Full content (escaped) for the expandable section
        full = p["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        rows += f"""
        <tr onclick="toggle({p['id']})" style="cursor:pointer">
          <td style="color:#8b949e;width:40px">#{p['id']}</td>
          <td style="width:100px">{date_str}</td>
          <td style="width:110px">
            <span style="background:{bg};color:{color};padding:3px 10px;border-radius:20px;
                         font-size:0.75rem;font-weight:600;white-space:nowrap">{label}</span>
          </td>
          <td style="color:#c9d1d9;font-size:0.85rem">{preview}</td>
        </tr>
        <tr id="expand-{p['id']}" style="display:none">
          <td colspan="4">
            <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;
                        padding:16px 20px;margin:4px 0 12px 0;font-size:0.85rem;
                        color:#c9d1d9;line-height:1.7;white-space:pre-wrap">{full}</div>
            <div style="font-size:0.75rem;color:#8b949e;padding:0 4px 10px">
              Posted at: {posted_str} &nbsp;|&nbsp; {len(p['content'])} characters
            </div>
          </td>
        </tr>
        """

    empty = "<tr><td colspan='4' style='text-align:center;color:#8b949e;padding:40px'>No posts yet. First post generates at 9:30 PM CST.</td></tr>" if not posts else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta http-equiv="refresh" content="60"/>
  <title>LinkedIn Agent Dashboard</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0 }}
    body {{ background:#0d1117; color:#e6edf3;
            font-family:'Segoe UI',system-ui,sans-serif; min-height:100vh }}

    header {{ background:linear-gradient(135deg,#161b22,#1c2a3a);
              border-bottom:1px solid #30363d; padding:24px 36px }}
    header h1 {{ font-size:1.4rem; font-weight:700; color:#58a6ff }}
    header p  {{ font-size:0.82rem; color:#8b949e; margin-top:5px }}

    .stats {{ display:flex; gap:16px; padding:20px 36px; flex-wrap:wrap }}
    .stat-card {{ background:#161b22; border:1px solid #21262d; border-radius:8px;
                  padding:14px 20px; min-width:140px }}
    .stat-card .num {{ font-size:1.6rem; font-weight:700 }}
    .stat-card .lbl {{ font-size:0.72rem; color:#8b949e; margin-top:3px;
                       text-transform:uppercase; letter-spacing:0.6px }}

    .table-wrap {{ padding:0 36px 40px }}
    table {{ width:100%; border-collapse:collapse }}
    thead th {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.6px;
                color:#8b949e; padding:10px 12px; text-align:left;
                border-bottom:1px solid #21262d }}
    tbody tr:hover td {{ background:#161b22 }}
    tbody td {{ padding:12px 12px; border-bottom:1px solid #161b22;
                vertical-align:middle }}

    .next-run {{ background:#161b22; border:1px solid #21262d; border-radius:8px;
                 padding:14px 20px; margin:0 36px 20px;
                 font-size:0.82rem; color:#8b949e }}
    .next-run span {{ color:#79c0ff; font-weight:600 }}
    .refresh-note {{ font-size:0.72rem; color:#484f58; margin:0 36px 16px }}
  </style>
</head>
<body>

<header>
  <h1>LinkedIn Auto-Post Agent</h1>
  <p>Live dashboard &mdash; click any row to expand the full post &nbsp;|&nbsp; auto-refreshes every 60 seconds</p>
</header>

<div class="stats">
  <div class="stat-card">
    <div class="num" style="color:#56d364">{sum(1 for p in posts if p['status']=='posted')}</div>
    <div class="lbl">Posted</div>
  </div>
  <div class="stat-card">
    <div class="num" style="color:#8b949e">{sum(1 for p in posts if p['status']=='skipped')}</div>
    <div class="lbl">Skipped</div>
  </div>
  <div class="stat-card">
    <div class="num" style="color:#f0883e">{sum(1 for p in posts if p['status']=='pending')}</div>
    <div class="lbl">Pending</div>
  </div>
  <div class="stat-card">
    <div class="num" style="color:#e6edf3">{len(posts)}</div>
    <div class="lbl">Total</div>
  </div>
</div>

<div class="next-run">
  Daily schedule (CST) &nbsp;&rarr;&nbsp;
  <span>9:30 PM</span> preview email &nbsp;&middot;&nbsp;
  <span>9:55 AM</span> approval check &nbsp;&middot;&nbsp;
  <span>10:00 AM</span> post to LinkedIn
</div>

<p class="refresh-note">Page auto-refreshes every 60 seconds</p>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Date</th>
        <th>Status</th>
        <th>Preview</th>
      </tr>
    </thead>
    <tbody>
      {rows}{empty}
    </tbody>
  </table>
</div>

<script>
  function toggle(id) {{
    const el = document.getElementById('expand-' + id);
    el.style.display = el.style.display === 'none' ? 'table-row' : 'none';
  }}
</script>

</body>
</html>"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
