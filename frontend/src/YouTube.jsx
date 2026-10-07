import { useEffect, useState } from "react";

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
