"""Adds the YouTube connector: fetch the public comments of a YouTube video through the official
YouTube Data API, run them through the existing moderation pipeline, and show them in a YouTube tab.
Put this file in the project root and run:  python add_youtube.py
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


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        fail("could not find (exactly once): " + what)
    return text.replace(old, new, 1)


P_VIEWS = path("backend", "api", "views.py")
P_URLS = path("backend", "api", "urls.py")
P_ROOT = path("frontend", "src", "Root.jsx")
P_NEW = path("frontend", "src", "YouTube.jsx")

for p in (P_VIEWS, P_URLS, P_ROOT):
    if not os.path.exists(p):
        fail("file not found: " + p + " (is this script in the project root?)")

v, u, r = read(P_VIEWS), read(P_URLS), read(P_ROOT)

if "def youtube_sync" in v or os.path.exists(P_NEW):
    fail("the YouTube connector is already installed.")
if "def _load_env_file" not in v:
    fail("the Instagram connector is missing (it provides the .env reader). Run add_instagram.py first.")

# BACKEND-START
BACKEND = '''


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
    m = re.search(r"(?:v=|youtu\\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", s)
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
                found.append({"id": top.get("id") or item.get("id", ""),
                              "text": s.get("textDisplay", ""), "author": s.get("authorDisplayName", "")})
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
        out = _process(text, "youtube", user, cid)
        results.append({
            "comment": text, "user_id": user, "comment_id": cid,
            "categories": out["categories"], "severity": out["severity"], "action": out["action"],
            "strikes": out["strikes"], "incident_id": out["incident_id"],
            "report_required": out["report_required"],
        })
    return JsonResponse({"video": vid, "fetched": len(found), "new": len(results),
                         "skipped": skipped, "results": results})
'''
# BACKEND-END

v += BACKEND

u = replace_once(u, '    path("posts/", views.posts),',
                 '    path("posts/", views.posts),\n'
                 '    path("youtube/status/", views.youtube_status),\n'
                 '    path("youtube/sync/", views.youtube_sync),',
                 "posts route in urls.py")

YOUTUBE_JSX = r'''import { useEffect, useState } from "react";

const SEV = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };

export default function YouTube() {
  const [configured, setConfigured] = useState(null);
  const [video, setVideo] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const fail = (e) => setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);

  const loadStatus = async () => {
    try {
      const res = await fetch("/api/youtube/status/");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setConfigured(data.configured); setError("");
    } catch (e) { fail(e); }
  };
  useEffect(() => { loadStatus(); }, []);

  const sync = async () => {
    if (!video.trim() || busy) return;
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/youtube/sync/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video, max: 100 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sync failed");
      setResult(data);
    } catch (e) { fail(e); }
    setBusy(false);
  };

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>YouTube comments</h2>
        <p className="muted" style={{ margin: 0 }}>
          Paste a YouTube video link. SafeComment AI reads its newest public comments through the official
          YouTube API, labels each one, and sends serious cases to the Incidents queue.
        </p>
      </div>

      <div className="card">
        <div className="ig-status">
          <span className={`ig-dot ${configured ? "on" : "off"}`} />
          {configured === null && !error && <span>Checking...</span>}
          {configured === true && <span><b>API key found</b></span>}
          {configured === false && <span><b>No API key yet</b></span>}
          <button className="ghost" onClick={loadStatus}>Check again</button>
        </div>
        {configured === false && (
          <ol className="ig-steps">
            <li>Open the <code>.env</code> file in the project's main folder.</li>
            <li>Add a new line: <code>YOUTUBE_API_KEY=your_key_here</code></li>
            <li>Stop the Django server (Ctrl+C) and start it again.</li>
            <li>Come back here and click <b>Check again</b>.</li>
          </ol>
        )}
        {error && <div className="error">{error}</div>}

        <div className="filters" style={{ marginTop: 14 }}>
          <input className="rev" style={{ flex: 1, minWidth: 220 }} placeholder="https://www.youtube.com/watch?v=..."
            value={video} onChange={(e) => setVideo(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") sync(); }} />
          <button className="btn" disabled={!configured || busy || !video.trim()} onClick={sync}>
            {busy ? "Fetching and analyzing..." : "Fetch and analyze comments"}
          </button>
        </div>
        <p className="muted" style={{ fontSize: 13, margin: "10px 0 0" }}>
          Reads up to 100 of the newest top-level comments. Comments already analyzed are skipped.
        </p>
      </div>

      {result && (
        <div className="card">
          <h3 style={{ margin: "0 0 4px" }}>Result</h3>
          <p className="muted" style={{ margin: "0 0 10px" }}>
            {result.fetched} comments found, {result.new} new analyzed, {result.skipped} skipped.
          </p>
          {result.results.length === 0 && <div className="empty">No new comments to analyze.</div>}
          {result.results.map((r) => (
            <div key={r.comment_id} className="row">
              <div className="row-main">
                <span className="muted">{r.user_id || "unknown user"}</span>
                <div className="row-text">{r.comment}</div>
              </div>
              <div className="row-res">
                <span className={`pill ${SEV[r.severity]}`}>{r.severity}</span>
                <span className="pill act">{r.action}</span>
                <span className="muted" style={{ fontSize: 13 }}>{r.categories.join(" + ")}</span>
                {r.strikes > 0 && <span className="pill review">strikes: {r.strikes}</span>}
                {r.report_required && <span className="pill cc-badge">Possible cybercrime</span>}
                {r.incident_id && <span className="muted" style={{ fontSize: 13 }}>incident #{r.incident_id}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
'''

r = replace_once(r, 'import Instagram from "./Instagram.jsx";\n',
                 'import Instagram from "./Instagram.jsx";\nimport YouTube from "./YouTube.jsx";\n',
                 "Instagram import in Root.jsx")
r = replace_once(r, '  ["ig", "Instagram"],\n',
                 '  ["ig", "Instagram"],\n  ["yt", "YouTube"],\n',
                 "Instagram tab entry in Root.jsx")
r = replace_once(r, '      {tab === "ig" && <Instagram />}\n',
                 '      {tab === "ig" && <Instagram />}\n      {tab === "yt" && <YouTube />}\n',
                 "Instagram render line in Root.jsx")

# every check passed: write all files
write(P_VIEWS, v)
write(P_URLS, u)
write(P_NEW, YOUTUBE_JSX)
write(P_ROOT, r)
print("youtube connector patched")
