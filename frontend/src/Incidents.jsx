import { useEffect, useState } from "react";

const SEV = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };

export default function Incidents() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("open");
  const [reviewer, setReviewer] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  const load = async () => {
    try {
      const res = await fetch("/api/incidents/?status=" + filter);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setRows(data.results); setError("");
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);
    }
  };
  useEffect(() => { load(); }, [filter]);

  const review = async (id, decision) => {
    if (!reviewer.trim()) { setError("Enter your name as reviewer first."); return; }
    setBusy(id);
    try {
      const res = await fetch(`/api/incidents/${id}/review/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, reviewer }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Review failed");
      setError(""); await load();
    } catch (e) { setError(e.message); }
    setBusy(null);
  };

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>Incident Review</h2>
        <p className="muted" style={{ margin: 0 }}>
          The AI flags content; a human decides. Reports for possible cybercrime are prepared here
          but must be filed by a person on the official portal.
        </p>
      </div>

      <div className="card">
        <div className="filters">
          <input className="rev" placeholder="Your name (reviewer)" value={reviewer}
            onChange={(e) => setReviewer(e.target.value)} />
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="open">Open</option>
            <option value="confirmed">Confirmed</option>
            <option value="dismissed">Dismissed</option>
            <option value="">All</option>
          </select>
          <button className="ghost" onClick={load}>Refresh</button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {rows.length === 0 && !error && <div className="empty">No incidents in this view.</div>}

      {rows.map((r) => (
        <div key={r.id} className={`card inc ${r.report_required ? "cc" : ""}`}>
          <div className="inc-top">
            <span className={`pill ${SEV[r.severity]}`}>{r.severity}</span>
            <span className="muted">#{r.id} - {r.platform} - user: {r.user_id || "n/a"} - strikes: {r.strikes}</span>
            {r.report_required && <span className="pill cc-badge">Possible cybercrime</span>}
            {r.restrict_user && <span className="pill review">Restrict user</span>}
            {r.report_count > 0 && <span className="pill review">Reported by {r.report_count}</span>}
          </div>
          <div className="inc-text">{r.comment}</div>
          <div className="muted" style={{ fontSize: 13 }}>
            {r.categories.join(" + ")} - {new Date(r.created_at).toLocaleString()}
          </div>
          {r.status === "open" ? (
            <div className="inc-actions">
              <button className="btn" disabled={busy === r.id} onClick={() => review(r.id, "confirmed")}>Confirm</button>
              <button className="ghost" disabled={busy === r.id} onClick={() => review(r.id, "dismissed")}>Dismiss</button>
            </div>
          ) : (
            <div className="inc-actions">
              <span className={`pill ${r.status === "confirmed" ? "sev-high" : "sev-none"}`}>
                {r.status} by {r.reviewed_by}
              </span>
              {r.status === "confirmed" && r.report_required && (
                <a className="ghost dl" href={`/api/incidents/${r.id}/report/`} download>Download evidence statement</a>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
