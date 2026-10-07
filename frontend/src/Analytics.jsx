import { useEffect, useState } from "react";

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
