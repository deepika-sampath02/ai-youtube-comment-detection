"""Adds moderation analytics (backend endpoint + Dashboard charts).
Put this file in the project root and run:  python add_analytics.py
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


P_VIEWS = path("backend", "api", "views.py")
P_URLS = path("backend", "api", "urls.py")
P_DASH = path("frontend", "src", "Dashboard.jsx")
P_CSS = path("frontend", "src", "Root.css")
P_NEW = path("frontend", "src", "Analytics.jsx")

for p in (P_VIEWS, P_URLS, P_DASH, P_CSS):
    if not os.path.exists(p):
        fail("file not found: " + p + " (is this script in the project root?)")

v, u, d, css = read(P_VIEWS), read(P_URLS), read(P_DASH), read(P_CSS)

if "def analytics" in v or os.path.exists(P_NEW):
    fail("analytics is already installed.")
if "CommentReport" not in v:
    fail("the report feature is missing. Run add_report_feature.py first.")

# ---------------- backend ----------------
v += '''


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
'''

old = '    path("posts/", views.posts),'
if old not in u:
    fail("could not find the posts route in urls.py")
u = u.replace(old, old + '\n    path("analytics/", views.analytics),', 1)

# ---------------- frontend ----------------
analytics_jsx = r'''import { useEffect, useState } from "react";

const CAT_COLORS = {
  "Normal": "#0E9F8E", "Offensive": "#F08A3C", "Harassment": "#E0A526",
  "Abusive": "#E5484D", "Threat": "#8B3FD9", "Sexual / 18+": "#B4235A",
};
const ACTION_COLORS = { ALLOW: "#0E9F8E", WARN: "#F08A3C", REMOVE: "#E5484D" };

function dayLabel(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" });
}

function DailyChart({ daily }) {
  const W = 560, H = 210, L = 8, T = 22, B = 30;
  const max = Math.max(1, ...daily.map((d) => d.total));
  const slot = (W - L * 2) / daily.length;
  const bw = slot * 0.56;
  const h = (n) => ((H - T - B) * n) / max;
  const summary = daily.map((d) => `${dayLabel(d.date)}: ${d.total} comments, ${d.flagged} flagged`).join("; ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="an-svg" role="img" aria-label={"Comments per day. " + summary}>
      <line x1={L} x2={W - L} y1={H - B} y2={H - B} stroke="#DCE3EE" />
      {daily.map((d, i) => {
        const x = L + i * slot + (slot - bw) / 2;
        const safe = d.total - d.flagged;
        return (
          <g key={d.date}>
            {safe > 0 && <rect x={x} y={H - B - h(d.total)} width={bw} height={h(safe)} fill="#0E9F8E" rx="3" />}
            {d.flagged > 0 && <rect x={x} y={H - B - h(d.flagged)} width={bw} height={h(d.flagged)} fill="#E5484D" rx="3" />}
            {d.total > 0 && (
              <text x={x + bw / 2} y={H - B - h(d.total) - 6} textAnchor="middle" fontSize="12" fontWeight="700" fill="#0B1F3A">{d.total}</text>
            )}
            <text x={x + bw / 2} y={H - 10} textAnchor="middle" fontSize="12" fill="#5B6B82">{dayLabel(d.date)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function Bars({ data, colors }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map((e) => e[1]));
  if (entries.length === 0) return <div className="muted">Nothing yet.</div>;
  return (
    <div className="an-bars">
      {entries.map(([k, n]) => (
        <div key={k} className="an-bar-row">
          <span className="an-bar-label">{k}</span>
          <div className="an-bar-track"><div className="an-bar-fill" style={{ width: `${(n / max) * 100}%`, background: colors[k] || "#5B6B82" }} /></div>
          <span className="an-bar-n">{n}</span>
        </div>
      ))}
    </div>
  );
}

export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch("/api/analytics/");
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || "Request failed");
        if (alive) { setData(body); setError(""); }
      } catch (e) {
        if (alive) setError(e.message === "Failed to fetch" ? "Cannot reach the server." : e.message);
      }
    };
    load();
    const id = setInterval(load, 8000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (error) return <div className="error">Analytics: {error}</div>;
  if (!data) return null;

  const total7 = data.daily.reduce((a, d) => a + d.total, 0);
  const flagged7 = data.daily.reduce((a, d) => a + d.flagged, 0);
  const rate = total7 ? Math.round((flagged7 / total7) * 100) : 0;
  const actionTotal = Object.values(data.actions).reduce((a, n) => a + n, 0);

  return (
    <>
      <div className="card">
        <div className="feed-head">
          <h3 style={{ margin: 0 }}>Comments in the last 7 days</h3>
          <span className="muted">{total7} analyzed, {flagged7} flagged ({rate}%)</span>
        </div>
        <DailyChart daily={data.daily} />
        <div className="legend">
          <span><i style={{ background: "#0E9F8E" }} />Allowed</span>
          <span><i style={{ background: "#E5484D" }} />Flagged (warned or removed)</span>
          <span>User reports: {data.reports}</span>
        </div>
      </div>

      <div className="an-grid">
        <div className="card">
          <h3 style={{ margin: "0 0 12px" }}>What kind of comments</h3>
          <Bars data={data.categories} colors={CAT_COLORS} />
          <p className="muted" style={{ fontSize: 13, margin: "10px 0 0" }}>A comment counts once in every category it matched.</p>
        </div>
        <div className="card">
          <h3 style={{ margin: "0 0 12px" }}>What the system did</h3>
          {actionTotal > 0 && (
            <div className="dist-bar">
              {["ALLOW", "WARN", "REMOVE"].filter((k) => data.actions[k]).map((k) => (
                <div key={k} className="dist-seg" style={{ width: `${(data.actions[k] / actionTotal) * 100}%`, background: ACTION_COLORS[k] }} title={`${k}: ${data.actions[k]}`} />
              ))}
            </div>
          )}
          <div className="legend">
            {["ALLOW", "WARN", "REMOVE"].map((k) => (
              <span key={k}><i style={{ background: ACTION_COLORS[k] }} />{k} {data.actions[k] || 0}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ margin: "0 0 4px" }}>Repeat offenders</h3>
        <p className="muted" style={{ fontSize: 13, margin: "0 0 10px" }}>
          Users with the most flagged comments. Restricted after {data.restrict_after} flagged comments.
        </p>
        {data.offenders.length === 0 ? (
          <div className="muted">No flagged users yet.</div>
        ) : (
          <table className="tbl">
            <thead><tr><th>User</th><th>Flagged</th><th>Total comments</th><th>Strikes</th><th>Status</th></tr></thead>
            <tbody>
              {data.offenders.map((o) => (
                <tr key={o.user_id}>
                  <td>{o.user_id}</td>
                  <td>{o.flagged}</td>
                  <td>{o.total}</td>
                  <td>{o.strikes}</td>
                  <td>{o.restricted ? <span className="pill sev-high">Restricted</span> : <span className="pill review">Watch</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
'''

old = 'import { useEffect, useRef, useState } from "react";\n'
if old not in d:
    fail("could not find the import line in Dashboard.jsx")
d = d.replace(old, old + 'import Analytics from "./Analytics.jsx";\n', 1)

old = '      <div className="card">\n        <div className="feed-head">'
if d.count(old) != 1:
    fail("could not find the latest-comments card in Dashboard.jsx")
d = d.replace(old, "      <Analytics />\n\n" + old, 1)

css += '''
.an-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.an-svg{width:100%;height:auto;display:block}
.an-bars{display:flex;flex-direction:column;gap:10px}
.an-bar-row{display:grid;grid-template-columns:110px 1fr 34px;gap:10px;align-items:center;font-size:14px}
.an-bar-track{height:12px;background:#EDF1F7;border-radius:6px;overflow:hidden}
.an-bar-fill{height:100%;border-radius:6px}
.an-bar-n{text-align:right;font-weight:700}
@media (max-width:760px){.an-grid{grid-template-columns:1fr}}
'''

# every check passed: write all files
write(P_VIEWS, v)
write(P_URLS, u)
write(P_NEW, analytics_jsx)
write(P_DASH, d)
write(P_CSS, css)
print("analytics patched")
