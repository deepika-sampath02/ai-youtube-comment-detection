"""Adds the Instagram connector: fetch comments from YOUR professional Instagram account,
run them through the existing moderation pipeline, and show them in a new Instagram tab.
Put this file in the project root and run:  python add_instagram.py
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
P_CSS = path("frontend", "src", "Root.css")
P_NEW = path("frontend", "src", "Instagram.jsx")

for p in (P_VIEWS, P_URLS, P_ROOT, P_CSS):
    if not os.path.exists(p):
        fail("file not found: " + p + " (is this script in the project root?)")

v, u, r, css = read(P_VIEWS), read(P_URLS), read(P_ROOT), read(P_CSS)

if "def instagram_sync" in v or os.path.exists(P_NEW):
    fail("the Instagram connector is already installed.")

# ---------------- backend ----------------
# BACKEND-START
BACKEND = '''


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
'''
# BACKEND-END

v += BACKEND

u = replace_once(u, '    path("posts/", views.posts),',
                 '    path("posts/", views.posts),\n'
                 '    path("instagram/status/", views.instagram_status),\n'
                 '    path("instagram/sync/", views.instagram_sync),',
                 "posts route in urls.py")

# ---------------- frontend ----------------
INSTAGRAM_JSX = r'''import { useEffect, useState } from "react";

const SEV = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };

export default function Instagram() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const fail = (e) => setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);

  const loadStatus = async () => {
    try {
      const res = await fetch("/api/instagram/status/");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setStatus(data); setError("");
    } catch (e) { fail(e); }
  };
  useEffect(() => { loadStatus(); }, []);

  const sync = async () => {
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/instagram/sync/", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sync failed");
      setResult(data);
    } catch (e) { fail(e); }
    setBusy(false);
  };

  const connected = status && status.connected;

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>Instagram connection</h2>
        <p className="muted" style={{ margin: 0 }}>
          SafeComment AI reads the comments on your own Instagram professional account, labels each one,
          and sends serious cases to the Incidents queue. A person always makes the final decision.
        </p>
      </div>

      <div className="card">
        <div className="ig-status">
          <span className={`ig-dot ${connected ? "on" : "off"}`} />
          {status === null && !error && <span>Checking connection...</span>}
          {status && connected && <span><b>Connected</b> as @{status.username}</span>}
          {status && !connected && <span><b>Not connected</b></span>}
          <button className="ghost" onClick={loadStatus}>Check again</button>
        </div>
        {status && !connected && <div className="error">{status.error}</div>}
        {error && <div className="error">{error}</div>}

        {status && !connected && (
          <ol className="ig-steps">
            <li>Create a file named <code>.env</code> in the project's main folder.</li>
            <li>Add one line to it: <code>INSTAGRAM_TOKEN=your_token_here</code></li>
            <li>Stop the Django server (Ctrl+C) and start it again.</li>
            <li>Come back here and click <b>Check again</b>.</li>
          </ol>
        )}

        <div className="filters" style={{ marginTop: 14 }}>
          <button className="btn" disabled={!connected || busy} onClick={sync}>
            {busy ? "Fetching and analyzing..." : "Fetch and analyze comments"}
          </button>
          <span className="muted">Checks your 10 latest posts. Comments already analyzed are skipped.</span>
        </div>
      </div>

      {result && (
        <div className="card">
          <h3 style={{ margin: "0 0 4px" }}>Result</h3>
          <p className="muted" style={{ margin: "0 0 10px" }}>
            {result.posts} posts checked, {result.fetched} comments found, {result.new} new analyzed, {result.skipped} skipped.
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

r = replace_once(r, 'import Feed from "./Feed.jsx";\n',
                 'import Feed from "./Feed.jsx";\nimport Instagram from "./Instagram.jsx";\n',
                 "Feed import in Root.jsx")
r = replace_once(r, '  ["feed", "Feed"],\n',
                 '  ["feed", "Feed"],\n  ["ig", "Instagram"],\n',
                 "feed tab entry in Root.jsx")
r = replace_once(r, '      {tab === "feed" && <Feed />}\n',
                 '      {tab === "feed" && <Feed />}\n      {tab === "ig" && <Instagram />}\n',
                 "feed render line in Root.jsx")

css += '''
.ig-status{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ig-dot{width:12px;height:12px;border-radius:50%;background:#9CA3AF;flex:none}
.ig-dot.on{background:#0E9F8E}
.ig-dot.off{background:#E5484D}
.ig-steps{margin:12px 0 0;padding-left:22px;line-height:1.8}
.ig-steps code{background:#EDF1F7;padding:1px 6px;border-radius:5px}
'''

# every check passed: write all files
write(P_VIEWS, v)
write(P_URLS, u)
write(P_NEW, INSTAGRAM_JSX)
write(P_ROOT, r)
write(P_CSS, css)
print("instagram connector patched")
