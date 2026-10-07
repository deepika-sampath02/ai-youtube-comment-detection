"""add_evidence_report.py

1. Saves the video ID, commenter channel ID and posting time for new YouTube comments.
2. Expands "Download report file" into a full evidence statement (links, times, AI scores,
   human reviewer, and an editable complaint paragraph). Wording: "possible cybercrime,
   to be confirmed by the authorities". Nothing is ever sent anywhere automatically.

Put this file in the project's main folder and run:  python add_evidence_report.py
It checks everything first and changes nothing if any check fails.
Backups: views.py.bak, models.py.bak, Incidents.jsx.bak (next to the originals).
"""
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))


def path(*parts):
    return os.path.join(ROOT, *parts)


def read(p):
    with open(p, encoding="utf8") as fh:
        return fh.read()


def write(p, text):
    with open(p, "w", encoding="utf8", newline="\n") as fh:
        fh.write(text)


def fail(msg):
    print("STOPPED - nothing was changed.")
    print("Reason:", msg)
    raise SystemExit(1)


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        fail("could not find (exactly once): " + what)
    return text.replace(old, new, 1)


P_VIEWS = path("backend", "api", "views.py")
P_MODELS = path("backend", "api", "models.py")
P_INC = path("frontend", "src", "Incidents.jsx")

for p in (P_VIEWS, P_MODELS, P_INC):
    if not os.path.exists(p):
        fail("file not found: " + p + " (is this script in the project's main folder?)")

v, m, inc = read(P_VIEWS), read(P_MODELS), read(P_INC)

if "author_channel_id" in m or "author_channel_id" in v:
    fail("the evidence report is already installed.")
if "def youtube_sync" not in v:
    fail("the YouTube connector is not installed (run add_youtube.py first).")

# ---------------- models.py: three new fields on Analysis ----------------
m = replace_once(
    m,
    "    reviewed_at = models.DateTimeField(null=True, blank=True)\n",
    "    reviewed_at = models.DateTimeField(null=True, blank=True)\n"
    "    # source details (filled for YouTube comments fetched after this update)\n"
    "    video_id = models.CharField(max_length=20, blank=True, default=\"\")\n"
    "    author_channel_id = models.CharField(max_length=100, blank=True, default=\"\")\n"
    "    posted_at = models.CharField(max_length=40, blank=True, default=\"\")\n",
    "reviewed_at field in models.py",
)

# ---------------- views.py: _process accepts the extra fields ----------------
v = replace_once(
    v,
    'def _process(comment, platform, user_id="", comment_id=""):',
    'def _process(comment, platform, user_id="", comment_id="", extra=None):',
    "_process signature",
)
v = replace_once(
    v,
    '        strikes=policy["strikes"], status="open" if policy["action"] == "REMOVE" else "none",\n    )',
    '        strikes=policy["strikes"], status="open" if policy["action"] == "REMOVE" else "none",\n'
    '        **(extra or {}),\n    )',
    "Analysis.objects.create call in _process",
)

# ---------------- views.py: youtube_sync keeps channel and time ----------------
v = replace_once(
    v,
    '''                found.append({"id": top.get("id") or item.get("id", ""),
                              "text": s.get("textDisplay", ""), "author": s.get("authorDisplayName", "")})''',
    '''                chan = s.get("authorChannelId") or {}
                found.append({"id": top.get("id") or item.get("id", ""),
                              "text": s.get("textDisplay", ""), "author": s.get("authorDisplayName", ""),
                              "channel": chan.get("value", "") if isinstance(chan, dict) else "",
                              "posted": s.get("publishedAt", "")})''',
    "found.append in youtube_sync",
)
v = replace_once(
    v,
    '        out = _process(text, "youtube", user, cid)',
    '        out = _process(text, "youtube", user, cid, extra={\n'
    '            "video_id": vid,\n'
    '            "author_channel_id": str(c.get("channel", ""))[:100],\n'
    '            "posted_at": str(c.get("posted", ""))[:40],\n'
    '        })',
    "_process call in youtube_sync",
)

# ---------------- views.py: new incident_report ----------------
NEW_REPORT = r'''def incident_report(request, pk):
    from django.http import HttpResponse
    try:
        a = Analysis.objects.exclude(status="none").get(pk=pk)
    except Analysis.DoesNotExist:
        return JsonResponse({"error": "incident not found"}, status=404)
    if not a.report_required:
        return JsonResponse({"error": "this incident is not flagged as possible cybercrime"}, status=400)
    if a.status != "confirmed":
        return JsonResponse({"error": "a human reviewer must confirm the incident first"}, status=400)

    na = "not recorded"
    vid = a.video_id
    is_yt = a.platform == "youtube"
    video_url = "https://www.youtube.com/watch?v=" + vid if (is_yt and vid) else na
    comment_url = ("https://www.youtube.com/watch?v=" + vid + "&lc=" + a.comment_id
                   if (is_yt and vid and a.comment_id) else na)
    channel_url = ("https://www.youtube.com/channel/" + a.author_channel_id
                   if (is_yt and a.author_channel_id) else na)
    prepared = timezone.now().isoformat()
    scores = ", ".join(k + "=" + str(val) for k, val in a.scores.items())

    lines = [
        "SAFECOMMENT AI - EVIDENCE STATEMENT (POSSIBLE CYBERCRIME)",
        "=" * 58,
        "Status: CONFIRMED BY A HUMAN REVIEWER. This is a possible cybercrime,",
        "to be confirmed by the authorities. AI output alone is not proof.",
        "",
        "INCIDENT",
        "-" * 58,
        "Incident ID        : SC-" + str(a.id),
        "Report prepared at : " + prepared + " (UTC)",
        "Platform           : " + a.platform,
        "",
        "SOURCE (copy these links as evidence)",
        "-" * 58,
        "Video link         : " + video_url,
        "Comment link       : " + comment_url,
        "Commenter name     : " + (a.user_id or na),
        "Commenter channel  : " + channel_url,
        "Comment ID         : " + (a.comment_id or na),
        "Posted at (UTC)    : " + (a.posted_at or na),
        "Fetched at (UTC)   : " + a.created_at.isoformat(),
        "",
        "COMMENT TEXT (exactly as posted)",
        "-" * 58,
        a.comment,
        "",
        "AI ANALYSIS (assists the reviewer, does not decide)",
        "-" * 58,
        "Categories         : " + a.categories,
        "Severity           : " + a.severity,
        "Suggested action   : " + a.action,
        "Scores             : " + scores,
        "Strikes on user    : " + str(a.strikes),
        "",
        "HUMAN REVIEW",
        "-" * 58,
        "Reviewed by        : " + a.reviewed_by,
        "Reviewed at (UTC)  : " + (a.reviewed_at.isoformat() if a.reviewed_at else ""),
        "",
        "DRAFT COMPLAINT (edit before submitting)",
        "-" * 58,
        "To the Cyber Crime Cell / National Cyber Crime Reporting Portal,",
        "",
        "I wish to report a publicly posted " + a.platform + " comment that I believe contains",
        "obscene, abusive or threatening content (" + a.categories + "). The comment, the",
        "commenter's name and channel, the video and the time of posting are recorded above.",
        "The comment was flagged by an automated tool and then reviewed and confirmed by",
        a.reviewed_by + ". I request that the authorities examine this matter and decide",
        "whether any law has been violated and what action is appropriate.",
        "",
        "Possibly applicable legal provisions: to be determined by the authorities.",
        "Complainant name and contact: [fill in before submitting]",
        "Date: [fill in]",
        "",
        "NEXT STEP",
        "-" * 58,
        "A person must submit this statement on the official portal: https://cybercrime.gov.in",
        "(helpline 1930 in India). Also use the platform's own Report option for the comment",
        "and the channel. Keep this file and screenshots of the comment as evidence.",
        "Open the comment link above soon: the comment may be deleted by its author.",
    ]
    resp = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="incident_SC-' + str(a.id) + '_evidence.txt"'
    return resp


'''

start_marker = "def incident_report(request, pk):"
end_marker = "SEED_POSTS = ["
if v.count(start_marker) != 1 or v.count(end_marker) != 1:
    fail("could not locate the incident_report function in views.py")
s, e = v.index(start_marker), v.index(end_marker)
if e < s:
    fail("unexpected order of code in views.py")
v = v[:s] + NEW_REPORT + v[e:]

# ---------------- Incidents.jsx: clearer button label ----------------
inc = replace_once(
    inc,
    'download>Download report file</a>',
    'download>Download evidence statement</a>',
    "Download report file link in Incidents.jsx",
)

# every check passed: back up, then write
for p in (P_VIEWS, P_MODELS, P_INC):
    shutil.copyfile(p, p + ".bak")
write(P_VIEWS, v)
write(P_MODELS, m)
write(P_INC, inc)
print("evidence report patched")
print("NEXT: run  python backend/manage.py makemigrations api   then   python backend/manage.py migrate")
