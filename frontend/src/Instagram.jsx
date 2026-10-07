import { useEffect, useState } from "react";

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
