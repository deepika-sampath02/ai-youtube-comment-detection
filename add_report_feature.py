"""Adds the 'Report comment' feature. Put this file in the project root and run:  python add_report_feature.py
It checks everything first and changes nothing if any check fails."""
import os

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


P_MODELS = path("backend", "api", "models.py")
P_VIEWS = path("backend", "api", "views.py")
P_URLS = path("backend", "api", "urls.py")
P_INC = path("frontend", "src", "Incidents.jsx")
P_FEED = path("frontend", "src", "Feed.jsx")

for p in (P_MODELS, P_VIEWS, P_URLS, P_INC, P_FEED):
    if not os.path.exists(p):
        fail("file not found: " + p + " (is this script in the project root?)")

m, v, u, i, f = read(P_MODELS), read(P_VIEWS), read(P_URLS), read(P_INC), read(P_FEED)

if "CommentReport" in m or "def report_comment" in v:
    fail("the report feature is already installed.")

# ---------------- models ----------------
if "class Comment(" not in m:
    fail("models.py has no Comment model. The Feed backend step must be applied first.")
m += '''

class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, related_name="reports", on_delete=models.CASCADE)
    reporter = models.CharField(max_length=100)
    reason = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "reporter")
'''

# ---------------- views ----------------
old = "from .models import Analysis, Comment, Post\n"
if old not in v:
    fail("could not find the models import line in views.py")
v = v.replace(old, "from .models import Analysis, Comment, CommentReport, Post\n", 1)

old = "from django.db.models import Count\n"
if old not in v:
    fail("could not find the Count import line in views.py")
v = v.replace(old, "from django.core.exceptions import ObjectDoesNotExist\n" + old, 1)

old = "def _row(a):\n"
if v.count(old) != 1:
    fail("could not find def _row in views.py")
v = v.replace(old, '''def _report_count(a):
    try:
        return a.feed_comment.reports.count()
    except ObjectDoesNotExist:
        return 0


''' + old, 1)

old = '        "created_at": a.created_at.isoformat(),\n    }'
if v.count(old) != 1:
    fail("could not find the end of _row in views.py")
v = v.replace(old, '        "created_at": a.created_at.isoformat(),\n        "report_count": _report_count(a),\n    }', 1)

v += '''


@csrf_exempt
@require_POST
@require_key
def report_comment(request, pk):
    # A user reports someone else's visible comment; it joins the incident queue for a moderator.
    try:
        c = Comment.objects.get(pk=pk)
    except Comment.DoesNotExist:
        return JsonResponse({"error": "comment not found"}, status=404)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    reporter = _clean_id(body.get("user_id"))
    reason = str(body.get("reason", "")).strip()[:100]
    if not reporter:
        return JsonResponse({"error": "user_id is required"}, status=400)
    if reporter == c.user_id:
        return JsonResponse({"error": "you cannot report your own comment"}, status=400)
    if c.state != "published":
        return JsonResponse({"error": "this comment is not visible"}, status=400)
    _, created = CommentReport.objects.get_or_create(comment=c, reporter=reporter, defaults={"reason": reason})
    if not created:
        return JsonResponse({"error": "you already reported this comment"}, status=400)
    a = c.analysis
    if a is not None and a.status == "none":
        a.status, a.needs_review = "open", True
        a.save()
    return JsonResponse({"reported": True, "reports": c.reports.count(),
                         "incident_id": a.id if a is not None and a.status == "open" else None})
'''

# ---------------- urls ----------------
old = '    path("posts/", views.posts),'
if old not in u:
    fail("could not find the posts route in urls.py")
u = u.replace(old, old + '\n    path("comments/<int:pk>/report/", views.report_comment),', 1)

# ---------------- incidents screen ----------------
old = '{r.restrict_user && <span className="pill review">Restrict user</span>}'
if old not in i:
    fail("could not find the Restrict user badge in Incidents.jsx")
i = i.replace(old, old + '\n            {r.report_count > 0 && <span className="pill review">Reported by {r.report_count}</span>}', 1)

# ---------------- feed screen ----------------
old = '  const [error, setError] = useState("");\n'
if f.count(old) != 1:
    fail("could not find the error state line in Feed.jsx")
f = f.replace(old, old + '  const [reported, setReported] = useState({});\n', 1)

old = "  const edit = (post, value) => {"
if f.count(old) != 1:
    fail("could not find the edit function in Feed.jsx")
fn = '''  const reportComment = async (id) => {
    try {
      const res = await fetch(`/api/comments/${id}/report/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user, reason: "reported by user" }),
      });
      const data = await res.json();
      if (!res.ok && !String(data.error || "").includes("already")) throw new Error(data.error || "Report failed");
      setReported((r) => ({ ...r, [id]: true }));
    } catch (e) { fail(e); }
  };

'''
f = f.replace(old, fn + old, 1)

marker = "Under review - only you can see this</span>}"
if marker not in f:
    fail("could not find the comment row in Feed.jsx")
idx = f.index(marker)
j = f.index("</div>", idx) + len("</div>")
btn = '''
                    {c.state === "published" && c.user_id !== user && (
                      reported[c.id]
                        ? <span className="fd-rep done">Reported</span>
                        : <button className="fd-rep" onClick={() => reportComment(c.id)}>Report</button>
                    )}'''
f = f[:j] + btn + f[j:]

# every check passed: write all files
write(P_MODELS, m)
write(P_VIEWS, v)
write(P_URLS, u)
write(P_INC, i)
write(P_FEED, f)
print("report feature patched")
