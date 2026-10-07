import json, os, sys
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Analysis, Comment, CommentReport, Post
from .policies import decide, RESTRICT_AFTER

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "ml"))
from moderator import Moderator

moderator = Moderator()   # loaded once at server start

MAX_LEN = 1000
PLATFORMS = {"instagram", "facebook", "youtube", "twitter", "custom"}


def require_key(view):
    """If SAFECOMMENT_API_KEY is set, every call must send it in the X-API-Key header."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        key = os.environ.get("SAFECOMMENT_API_KEY", "")
        if key and request.headers.get("X-API-Key") != key:
            return JsonResponse({"error": "invalid or missing API key"}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _confidence(result):
    top = max(result["scores"].values())
    return top if result["categories"] != ["Normal"] else 1 - top


def _platform(value):
    value = str(value or "custom").lower()
    return value if value in PLATFORMS else "custom"


def _clean_id(value):
    return str(value or "").strip()[:100]


def _process(comment, platform, user_id="", comment_id="", extra=None):
    result = moderator.analyze(comment[:MAX_LEN])
    prior = (Analysis.objects.filter(user_id=user_id).exclude(action="ALLOW").count()
             if user_id else 0)
    policy = decide(result, prior)
    a = Analysis.objects.create(
        comment=result["comment"], platform=platform, user_id=user_id, comment_id=comment_id,
        categories=", ".join(result["categories"]), severity=result["severity"],
        needs_review=result["needs_review"], confidence=round(_confidence(result), 4),
        scores=result["scores"], action=policy["action"], escalate=policy["escalate"],
        report_required=policy["report_required"], restrict_user=policy["restrict_user"],
        strikes=policy["strikes"], status="open" if policy["action"] == "REMOVE" else "none",
        **(extra or {}),
    )
    result.update(policy)
    result["incident_id"] = a.id if a.status == "open" else None
    result["analysis_id"] = a.id
    return result


def _report_count(a):
    try:
        return a.feed_comment.reports.count()
    except ObjectDoesNotExist:
        return 0


def _row(a):
    return {
        "id": a.id, "comment": a.comment, "platform": a.platform,
        "user_id": a.user_id, "comment_id": a.comment_id,
        "categories": a.categories.split(", "), "severity": a.severity,
        "needs_review": a.needs_review, "confidence": a.confidence, "scores": a.scores,
        "action": a.action, "escalate": a.escalate, "report_required": a.report_required,
        "restrict_user": a.restrict_user, "strikes": a.strikes,
        "status": a.status, "reviewed_by": a.reviewed_by,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "created_at": a.created_at.isoformat(),
        "report_count": _report_count(a),
    }


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
@require_key
def moderate(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    comment = str(body.get("comment", "")).strip()
    if not comment:
        return JsonResponse({"error": "comment is required"}, status=400)
    if len(comment) > MAX_LEN:
        return JsonResponse({"error": f"comment is too long (max {MAX_LEN} characters)"}, status=400)
    return JsonResponse(_process(comment, _platform(body.get("platform")),
                                 _clean_id(body.get("user_id")), _clean_id(body.get("comment_id"))))


@csrf_exempt
@require_POST
@require_key
def moderate_batch(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    platform = _platform(body.get("platform"))
    results = []
    for item in body.get("comments", [])[:100]:
        if isinstance(item, dict):
            text, uid, cid = str(item.get("comment", "")), item.get("user_id"), item.get("comment_id")
        else:
            text, uid, cid = str(item), "", ""
        text = text.strip()
        if text:
            results.append(_process(text, platform, _clean_id(uid), _clean_id(cid)))
    return JsonResponse({"results": results})


@require_GET
@require_key
def history(request):
    qs = Analysis.objects.all()
    g = request.GET
    if g.get("severity"):
        qs = qs.filter(severity=g["severity"].upper())
    if g.get("category"):
        qs = qs.filter(categories__icontains=g["category"])
    if g.get("platform"):
        qs = qs.filter(platform=g["platform"].lower())
    if g.get("user_id"):
        qs = qs.filter(user_id=g["user_id"])
    if g.get("action"):
        qs = qs.filter(action=g["action"].upper())
    if g.get("review") == "1":
        qs = qs.filter(needs_review=True)
    try:
        limit = max(1, min(int(g.get("limit", 50)), 200))
    except ValueError:
        limit = 50
    return JsonResponse({"count": qs.count(), "results": [_row(a) for a in qs[:limit]]})


@require_GET
@require_key
def stats(request):
    by_sev = {r["severity"]: r["n"] for r in Analysis.objects.values("severity").annotate(n=Count("id"))}
    total = Analysis.objects.count()
    return JsonResponse({
        "total": total,
        "safe": by_sev.get("NONE", 0),
        "flagged": total - by_sev.get("NONE", 0),
        "needs_review": Analysis.objects.filter(needs_review=True).count(),
        "open_incidents": Analysis.objects.filter(status="open").count(),
        "possible_cybercrime": Analysis.objects.filter(report_required=True, status__in=["open", "confirmed"]).count(),
        "by_severity": by_sev,
    })


@require_GET
@require_key
def incidents(request):
    qs = Analysis.objects.exclude(status="none")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"].lower())
    if request.GET.get("cybercrime") == "1":
        qs = qs.filter(report_required=True)
    return JsonResponse({"count": qs.count(), "results": [_row(a) for a in qs[:100]]})


@csrf_exempt
@require_POST
@require_key
def review_incident(request, pk):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    decision = str(body.get("decision", "")).lower()
    reviewer = str(body.get("reviewer", "")).strip()[:100]
    if decision not in ("confirmed", "dismissed"):
        return JsonResponse({"error": "decision must be 'confirmed' or 'dismissed'"}, status=400)
    if not reviewer:
        return JsonResponse({"error": "reviewer is required"}, status=400)
    try:
        a = Analysis.objects.exclude(status="none").get(pk=pk)
    except Analysis.DoesNotExist:
        return JsonResponse({"error": "incident not found"}, status=404)
    a.status, a.reviewed_by, a.reviewed_at = decision, reviewer, timezone.now()
    a.save()
    # keep the feed in step with the reviewer: dismissed -> comment appears, confirmed -> removed
    Comment.objects.filter(analysis=a).update(state="published" if decision == "dismissed" else "removed")
    return JsonResponse(_row(a))

@csrf_exempt
@require_GET
@require_key
def incident_report(request, pk):
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


SEED_POSTS = [
    ("maya_k", "Weekend in Pondicherry", "#F59E8B", 245),
    ("ravi_22", "Sunrise run, 10 km done", "#7CC6C0", 132),
    ("nina_b", "My first painting of the year", "#B79CED", 318),
    ("dev_sam", "New desk setup is finally ready", "#8FB8E8", 97),
    ("kiran_p", "Sunday biryani, no regrets", "#F2C46D", 411),
]


def _seed_posts():
    if Post.objects.exists():
        return
    for author, caption, color, likes in SEED_POSTS:
        Post.objects.create(author=author, caption=caption, color=color, likes=likes)


def _comment_row(c):
    return {"id": c.id, "user_id": c.user_id, "text": c.text, "state": c.state,
            "created_at": c.created_at.isoformat()}


@require_GET
@require_key
def posts(request):
    """Feed. Published comments are public; a user also sees their own held comments (?viewer=)."""
    _seed_posts()
    viewer = _clean_id(request.GET.get("viewer"))
    out = []
    for p in Post.objects.prefetch_related("comments"):
        allc = list(p.comments.all())
        shown = [c for c in allc if c.state == "published"
                 or (c.state == "held" and viewer and c.user_id == viewer)]
        out.append({
            "id": p.id, "author": p.author, "caption": p.caption, "color": p.color,
            "likes": p.likes, "created_at": p.created_at.isoformat(),
            "comment_count": sum(1 for c in allc if c.state == "published"),
            "comments": [_comment_row(c) for c in shown],
        })
    return JsonResponse({"results": out})


@csrf_exempt
@require_POST
@require_key
def post_comment(request, pk):
    """Moderate a comment before it appears.
    outcome: published | confirm (warned, user must confirm) | held (sent to a moderator)."""
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return JsonResponse({"error": "post not found"}, status=404)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    text = str(body.get("comment", "")).strip()
    user = _clean_id(body.get("user_id"))
    if not text:
        return JsonResponse({"error": "comment is required"}, status=400)
    if len(text) > MAX_LEN:
        return JsonResponse({"error": f"comment is too long (max {MAX_LEN} characters)"}, status=400)
    if not user:
        return JsonResponse({"error": "user_id is required"}, status=400)

    restricted = Analysis.objects.filter(user_id=user).exclude(action="ALLOW").count() >= RESTRICT_AFTER

    # Second step: the user chose to post a warned comment anyway (no new analysis, no new strike).
    if body.get("confirm_analysis_id"):
        try:
            a = Analysis.objects.get(pk=int(body["confirm_analysis_id"]), user_id=user, action="WARN")
        except (Analysis.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"error": "nothing to confirm"}, status=400)
        if a.comment != text:
            return JsonResponse({"error": "comment changed; send it again for a new check"}, status=400)
        if Comment.objects.filter(analysis=a).exists():
            return JsonResponse({"error": "this comment was already posted"}, status=400)
        if restricted:
            a.status, a.needs_review = "open", True
            a.save()
            c = Comment.objects.create(post=post, user_id=user, text=text, state="held", analysis=a)
            return JsonResponse({"outcome": "held", "restricted": True, "incident_id": a.id, "comment": _comment_row(c)})
        c = Comment.objects.create(post=post, user_id=user, text=text, state="published", analysis=a)
        return JsonResponse({"outcome": "published", "comment": _comment_row(c)})

    result = _process(text, "custom", user, "")
    base = {"categories": result["categories"], "severity": result["severity"],
            "action": result["action"], "analysis_id": result["analysis_id"]}
    if restricted and result["action"] in ("ALLOW", "WARN"):
        a = Analysis.objects.get(pk=result["analysis_id"])
        a.status, a.needs_review = "open", True
        a.save()
        c = Comment.objects.create(post=post, user_id=user, text=text, state="held", analysis=a)
        return JsonResponse({**base, "outcome": "held", "restricted": True, "incident_id": a.id, "comment": _comment_row(c)})
    if result["action"] == "ALLOW":
        a = Analysis.objects.get(pk=result["analysis_id"])
        c = Comment.objects.create(post=post, user_id=user, text=text, state="published", analysis=a)
        return JsonResponse({**base, "outcome": "published", "comment": _comment_row(c)})
    if result["action"] == "WARN":
        return JsonResponse({**base, "outcome": "confirm", "comment": None})
    a = Analysis.objects.get(pk=result["analysis_id"])
    c = Comment.objects.create(post=post, user_id=user, text=text, state="held", analysis=a)
    return JsonResponse({**base, "outcome": "held", "incident_id": result["incident_id"],
                         "comment": _comment_row(c)})



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



@require_GET
@require_key
def analytics(request):
    """Numbers for the dashboard charts: last 7 days, category and action mix, repeat offenders."""
    from datetime import timedelta
    from .models import CommentReport
    from .policies import RESTRICT_AFTER

    rows = list(Analysis.objects.all().only("created_at", "categories", "action", "user_id", "strikes"))
    today = timezone.localdate()
    days = [today - timedelta(days=n) for n in range(6, -1, -1)]
    daily = {day: {"date": day.isoformat(), "total": 0, "flagged": 0} for day in days}
    categories, actions, users = {}, {}, {}

    for a in rows:
        day = timezone.localtime(a.created_at).date()
        if day in daily:
            daily[day]["total"] += 1
            if a.action != "ALLOW":
                daily[day]["flagged"] += 1
        for cat in a.categories.split(", "):
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
        actions[a.action] = actions.get(a.action, 0) + 1
        if a.user_id:
            row = users.setdefault(a.user_id, {"user_id": a.user_id, "total": 0, "flagged": 0, "strikes": 0})
            row["total"] += 1
            row["strikes"] = max(row["strikes"], a.strikes)
            if a.action != "ALLOW":
                row["flagged"] += 1

    offenders = sorted((r for r in users.values() if r["flagged"] > 0),
                       key=lambda r: (-r["flagged"], r["user_id"]))[:5]
    for r in offenders:
        r["restricted"] = r["flagged"] >= RESTRICT_AFTER

    return JsonResponse({
        "daily": [daily[day] for day in days],
        "categories": categories,
        "actions": actions,
        "offenders": offenders,
        "reports": CommentReport.objects.count(),
        "restrict_after": RESTRICT_AFTER,
    })



# ----------------------------------------------------------------------------
# Instagram connector (Instagram API with Instagram Login, your own professional account)
# The access token is read from the INSTAGRAM_TOKEN environment variable or from a .env file
# in the project root. It is never sent to the browser or written to the database.
# ----------------------------------------------------------------------------
class IGError(Exception):
    pass


def _load_env_file():
    out = {}
    try:
        with open(os.path.join(ROOT, ".env"), encoding="utf8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    out[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def _ig_token():
    return os.environ.get("INSTAGRAM_TOKEN") or _load_env_file().get("INSTAGRAM_TOKEN", "")


def _ig_get(api_path, params=None):
    import urllib.error
    import urllib.parse
    import urllib.request
    token = _ig_token()
    if not token:
        raise IGError("INSTAGRAM_TOKEN is not set. Put it in a .env file in the project root, then restart the server.")
    query = dict(params or {})
    query["access_token"] = token
    url = "https://graph.instagram.com/" + api_path.lstrip("/") + "?" + urllib.parse.urlencode(query)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf8")).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        raise IGError("Instagram said: " + (msg or "HTTP %s" % e.code))
    except (urllib.error.URLError, OSError):
        raise IGError("Cannot reach Instagram. Check your internet connection.")


@require_GET
@require_key
def instagram_status(request):
    if not _ig_token():
        return JsonResponse({"connected": False,
                             "error": "No token yet. Put INSTAGRAM_TOKEN in a .env file in the project root and restart the server."})
    try:
        me = _ig_get("me", {"fields": "user_id,username"})
    except IGError as e:
        return JsonResponse({"connected": False, "error": str(e)})
    return JsonResponse({"connected": True, "username": me.get("username", "")})


@csrf_exempt
@require_POST
@require_key
def instagram_sync(request):
    """Fetch comments on your latest posts and moderate the ones we have not seen yet."""
    try:
        me = _ig_get("me", {"fields": "user_id,username"})
        own = str(me.get("username", "")).lower()
        media = _ig_get("me/media", {"fields": "id,caption,timestamp,permalink", "limit": 10}).get("data", [])
        found = []
        for m in media:
            data = _ig_get(str(m["id"]) + "/comments",
                           {"fields": "id,text,timestamp,username", "limit": 50}).get("data", [])
            for c in data:
                found.append((m, c))
    except IGError as e:
        return JsonResponse({"error": str(e)}, status=502)

    ids = [str(c.get("id", "")) for _, c in found if c.get("id")]
    seen = set(Analysis.objects.filter(platform="instagram", comment_id__in=ids)
               .values_list("comment_id", flat=True))
    results, skipped = [], 0
    for m, c in found:
        cid = _clean_id(c.get("id"))
        text = str(c.get("text", "")).strip()
        user = _clean_id(c.get("username"))
        if not cid or not text or cid in seen or (user and user.lower() == own):
            skipped += 1
            continue
        seen.add(cid)
        out = _process(text, "instagram", user, cid)
        results.append({
            "comment": text, "user_id": user, "comment_id": cid,
            "categories": out["categories"], "severity": out["severity"], "action": out["action"],
            "strikes": out["strikes"], "incident_id": out["incident_id"],
            "report_required": out["report_required"],
        })
    return JsonResponse({"posts": len(media), "fetched": len(found), "new": len(results),
                         "skipped": skipped, "results": results})



# ----------------------------------------------------------------------------
# YouTube connector (YouTube Data API v3, public comments of a video)
# The API key is read from the YOUTUBE_API_KEY environment variable or from the .env file in the
# project root. It is never sent to the browser or written to the database.
# ----------------------------------------------------------------------------
class YTError(Exception):
    pass


def _yt_key():
    return os.environ.get("YOUTUBE_API_KEY") or _load_env_file().get("YOUTUBE_API_KEY", "")


def _yt_video_id(value):
    import re
    s = str(value or "").strip()
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    return ""


def _yt_get(params):
    import urllib.error
    import urllib.parse
    import urllib.request
    key = _yt_key()
    if not key:
        raise YTError("YOUTUBE_API_KEY is not set. Put it in the .env file in the project root, then restart the server.")
    query = dict(params)
    query["key"] = key
    url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urllib.parse.urlencode(query)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf8")).get("error", {})
            msg = err.get("message", "")
            reasons = [x.get("reason", "") for x in err.get("errors", [])]
        except Exception:
            msg, reasons = "", []
        if "commentsDisabled" in reasons:
            raise YTError("Comments are turned off on this video.")
        if "videoNotFound" in reasons:
            raise YTError("Video not found. Check the link.")
        raise YTError("YouTube said: " + (msg or "HTTP %s" % e.code))
    except (urllib.error.URLError, OSError):
        raise YTError("Cannot reach YouTube. Check your internet connection.")


@require_GET
@require_key
def youtube_status(request):
    return JsonResponse({"configured": bool(_yt_key())})


@csrf_exempt
@require_POST
@require_key
def youtube_sync(request):
    """Fetch the newest public comments of one video and moderate the ones we have not seen yet."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    vid = _yt_video_id(body.get("video"))
    if not vid:
        return JsonResponse({"error": "Paste a YouTube video link or the 11-character video ID."}, status=400)
    try:
        want = max(1, min(int(body.get("max", 100)), 200))
    except (TypeError, ValueError):
        want = 100

    found, token = [], None
    try:
        while len(found) < want:
            params = {"part": "snippet", "videoId": vid, "maxResults": min(100, want - len(found)),
                      "order": "time", "textFormat": "plainText"}
            if token:
                params["pageToken"] = token
            data = _yt_get(params)
            for item in data.get("items", []):
                top = item.get("snippet", {}).get("topLevelComment", {})
                s = top.get("snippet", {})
                chan = s.get("authorChannelId") or {}
                found.append({"id": top.get("id") or item.get("id", ""),
                              "text": s.get("textDisplay", ""), "author": s.get("authorDisplayName", ""),
                              "channel": chan.get("value", "") if isinstance(chan, dict) else "",
                              "posted": s.get("publishedAt", "")})
            token = data.get("nextPageToken")
            if not token:
                break
    except YTError as e:
        return JsonResponse({"error": str(e)}, status=502)

    ids = [str(c["id"]) for c in found if c["id"]]
    seen = set(Analysis.objects.filter(platform="youtube", comment_id__in=ids)
               .values_list("comment_id", flat=True))
    results, skipped = [], 0
    for c in found:
        cid = _clean_id(c["id"])
        text = str(c["text"]).strip()
        user = _clean_id(c["author"])
        if not cid or not text or cid in seen:
            skipped += 1
            continue
        seen.add(cid)
        out = _process(text, "youtube", user, cid, extra={
            "video_id": vid,
            "author_channel_id": str(c.get("channel", ""))[:100],
            "posted_at": str(c.get("posted", ""))[:40],
        })
        results.append({
            "comment": text, "user_id": user, "comment_id": cid,
            "categories": out["categories"], "severity": out["severity"], "action": out["action"],
            "strikes": out["strikes"], "incident_id": out["incident_id"],
            "report_required": out["report_required"],
        })
    return JsonResponse({"video": vid, "fetched": len(found), "new": len(results),
                         "skipped": skipped, "results": results})
