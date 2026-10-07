import { useEffect, useState } from "react";

const SEV = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };

export default function History() {
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [severity, setSeverity] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const q = "?limit=100" + (severity ? "&severity=" + severity : "");
      const [h, s] = await Promise.all([fetch("/api/history/" + q), fetch("/api/stats/")]);
      const hd = await h.json();
      const sd = await s.json();
      if (!h.ok) throw new Error(hd.error || "Request failed");
      if (!s.ok) throw new Error(sd.error || "Request failed");
      setRows(hd.results); setStats(sd); setError("");
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);
    }
  };
  useEffect(() => { load(); }, [severity]);

  const STAT_LABELS = [
    ["total", "Total analyzed"], ["safe", "Safe"], ["flagged", "Flagged"],
    ["needs_review", "Needs review"], ["open_incidents", "Open incidents"],
    ["possible_cybercrime", "Possible cybercrime"],
  ];

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>History</h2>
        <p className="muted" style={{ margin: 0 }}>Every comment the system has analyzed, newest first.</p>
      </div>

      {stats && (
        <div className="stats">
          {STAT_LABELS.map(([k, label]) => (
            <div key={k} className="card stat">
              <div className="stat-n">{stats[k]}</div>
              <div className="muted" style={{ fontSize: 13 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="card filters">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          <option value="NONE">None</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
        <button className="ghost" onClick={load}>Refresh</button>
      </div>
      {error && <div className="error">{error}</div>}
      {rows.length === 0 && !error && <div className="empty">Nothing here yet.</div>}

      {rows.length > 0 && (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr><th>Time</th><th>Severity</th><th>Categories</th><th>Action</th><th>User</th><th>Comment</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{new Date(r.created_at).toLocaleString()}</td>
                  <td><span className={`pill ${SEV[r.severity]}`}>{r.severity}</span></td>
                  <td>{r.categories.join(" + ")}</td>
                  <td>{r.action}</td>
                  <td>{r.user_id || "n/a"}</td>
                  <td>{r.comment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
