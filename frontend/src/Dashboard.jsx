import { useEffect, useRef, useState } from "react";
import Analytics from "./Analytics.jsx";

const COLORS = { NONE: "#0E9F8E", LOW: "#E0A526", MEDIUM: "#F08A3C", HIGH: "#E5484D", CRITICAL: "#8B3FD9" };
const LABELS = { NONE: "Safe", LOW: "Low", MEDIUM: "Medium", HIGH: "High", CRITICAL: "Critical" };
const PILL = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };
const ORDER = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

function useCount(target) {
  const [v, setV] = useState(0);
  const prev = useRef(0);
  useEffect(() => {
    const to = target || 0;
    const from = prev.current;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setV(to); prev.current = to; return;
    }
    const t0 = performance.now();
    let raf;
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / 700);
      setV(Math.round(from + (to - from) * p));
      if (p < 1) raf = requestAnimationFrame(tick); else prev.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return v;
}

function hue(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }

function ago(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h ago";
  return Math.floor(s / 86400) + " d ago";
}

function StatCard({ label, value, tone }) {
  const n = useCount(value);
  return (
    <div className={`dstat tone-${tone}`}>
      <div className="dstat-n">{n}</div>
      <div className="dstat-l">{label}</div>
    </div>
  );
}

export default function Dashboard({ go }) {
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [s, h] = await Promise.all([fetch("/api/stats/"), fetch("/api/history/?limit=8")]);
      const sd = await s.json();
      const hd = await h.json();
      if (!s.ok) throw new Error(sd.error || "Request failed");
      if (!h.ok) throw new Error(hd.error || "Request failed");
      setStats(sd); setRows(hd.results); setError("");
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);
    }
  };
  useEffect(() => {
    load();
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, []);

  const by = (stats && stats.by_severity) || {};
  const total = ORDER.reduce((a, k) => a + (by[k] || 0), 0);

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>Moderation dashboard</h2>
        <p className="muted" style={{ margin: 0 }}>
          A live view of what the system has analyzed, what it flagged, and what is waiting for a human decision.
        </p>
        <span className={`live ${error ? "off" : ""}`}><i />{error ? "Offline" : "Live - refreshes every 8 seconds"}</span>
      </div>

      {error && <div className="error">{error}</div>}

      {stats && (
        <div className="dstats">
          <StatCard label="Comments analyzed" value={stats.total} tone="blue" />
          <StatCard label="Safe" value={stats.safe} tone="green" />
          <StatCard label="Flagged" value={stats.flagged} tone="orange" />
          <StatCard label="Open incidents" value={stats.open_incidents} tone="red" />
          <StatCard label="Possible cybercrime" value={stats.possible_cybercrime} tone="dark" />
        </div>
      )}

      {stats && stats.total === 0 && (
        <div className="card empty-hero">
          <h3 style={{ margin: "0 0 6px" }}>Nothing analyzed yet</h3>
          <p className="muted" style={{ margin: "0 0 14px" }}>Fetch comments from a YouTube video to see this dashboard fill with real results.</p>
          <button className="btn" onClick={() => go("yt")}>Open YouTube</button>
        </div>
      )}

      {stats && stats.total > 0 && (
        <div className="card">
          <h3 style={{ margin: "0 0 12px" }}>How severe are the comments?</h3>
          <div className="dist-bar">
            {ORDER.filter((k) => by[k]).map((k) => (
              <div key={k} className="dist-seg" style={{ width: `${(by[k] / total) * 100}%`, background: COLORS[k] }}
                title={`${LABELS[k]}: ${by[k]}`} />
            ))}
          </div>
          <div className="legend">
            {ORDER.map((k) => (
              <span key={k}><i style={{ background: COLORS[k] }} />{LABELS[k]} {by[k] || 0}</span>
            ))}
          </div>
        </div>
      )}

      <Analytics />

      <div className="card">
        <div className="feed-head">
          <h3 style={{ margin: 0 }}>Latest comments</h3>
          <div className="quick">
            <button className="ghost" onClick={() => go("tester")}>Test a comment</button>
            <button className="ghost" onClick={() => go("yt")}>Fetch YouTube comments</button>
            <button className="btn" onClick={() => go("incidents")}>Review incidents</button>
          </div>
        </div>
        {rows.length === 0 && !error && <div className="empty">No comments yet.</div>}
        {rows.map((r) => {
          const who = r.user_id || "guest";
          return (
            <div key={r.id} className="feed-row" style={{ borderLeftColor: COLORS[r.severity] || COLORS.NONE }}>
              <div className="av" style={{ background: `hsl(${hue(who)} 55% 42%)` }}>{who.charAt(0).toUpperCase()}</div>
              <div className="feed-main">
                <div className="muted" style={{ fontSize: 13 }}>{who} - {r.platform} - {ago(r.created_at)}</div>
                <div className="feed-text">{r.comment}</div>
              </div>
              <div className="feed-pills">
                <span className={`pill ${PILL[r.severity]}`}>{r.severity}</span>
                <span className="pill act">{r.action}</span>
                <span className="muted" style={{ fontSize: 13 }}>{r.categories.join(" + ")}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
