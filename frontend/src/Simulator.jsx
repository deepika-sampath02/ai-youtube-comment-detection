import { useState } from "react";

const SEV = { NONE: "sev-none", LOW: "sev-low", MEDIUM: "sev-medium", HIGH: "sev-high", CRITICAL: "sev-critical" };
const COLORS = { NONE: "#0E9F8E", LOW: "#E0A526", MEDIUM: "#F08A3C", HIGH: "#E5484D", CRITICAL: "#8B3FD9" };

const POSTS = [
  { id: "p1", platform: "instagram", title: "Instagram - Weekend travel reel", comments: [
    { id: "p1c1", user: "maya_k", text: "Where did you get this dress from?" },
    { id: "p1c2", user: "ravi_22", text: "Congrats!! You deserve more subscribers" },
    { id: "p1c3", user: "troll_99", text: "You are an idiot" },
    { id: "p1c4", user: "troll_99", text: "I know where you live" },
    { id: "p1c5", user: "anon_x7", text: "Can you send me some nude photos" },
  ] },
  { id: "p2", platform: "youtube", title: "YouTube - Python tutorial", comments: [
    { id: "p2c1", user: "dev_sam", text: "Your explanation was very clear, thank you" },
    { id: "p2c2", user: "troll_99", text: "You better watch yourself" },
    { id: "p2c3", user: "nina_b", text: "Please make a part 2" },
    { id: "p2c4", user: "anon_x7", text: "Stop posting this garbage" },
    { id: "p2c5", user: "kiran_p", text: "The ending was unexpected lol" },
  ] },
];

function hue(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }

export default function Simulator() {
  const [results, setResults] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const analyzeAll = async () => {
    setBusy(true); setError("");
    try {
      const out = {};
      for (const post of POSTS) {
        const res = await fetch("/api/moderate-batch/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            platform: post.platform,
            comments: post.comments.map((c) => ({ comment: c.text, user_id: c.user, comment_id: c.id })),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");
        post.comments.forEach((c, i) => { out[c.id] = data.results[i]; });
      }
      setResults(out);
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);
    }
    setBusy(false);
  };

  const all = Object.values(results);
  const flagged = all.filter((r) => r.severity !== "NONE").length;
  const incidents = all.filter((r) => r.incident_id).length;

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>Social Simulator</h2>
        <p className="muted" style={{ margin: 0 }}>
          A fake feed of comments. Each comment is sent to the moderation API with a user ID,
          so repeat offenders collect strikes.
        </p>
      </div>

      <div className="card filters">
        <button className="btn" disabled={busy} onClick={analyzeAll}>
          {busy ? "Analyzing..." : "Analyze all comments"}
        </button>
        {all.length > 0 && (
          <span className="muted">{all.length} analyzed, {flagged} flagged, {incidents} incidents opened</span>
        )}
      </div>
      {error && <div className="error">{error}</div>}

      {POSTS.map((post) => (
        <div key={post.id} className="card">
          <h3 style={{ margin: "0 0 10px" }}>{post.title}</h3>
          {post.comments.map((c) => {
            const r = results[c.id];
            return (
              <div key={c.id} className="row sim-row" style={{ borderLeftColor: r ? COLORS[r.severity] : "transparent" }}>
                <div className="av" style={{ background: `hsl(${hue(c.user)} 55% 42%)` }}>{c.user.charAt(0).toUpperCase()}</div>
                <div className="row-main">
                  <span className="muted">{c.user}</span>
                  <div className="row-text">{c.text}</div>
                </div>
                {r && (
                  <div className="row-res">
                    <span className={`pill ${SEV[r.severity]}`}>{r.severity}</span>
                    <span className="pill act">{r.action}</span>
                    <span className="muted" style={{ fontSize: 13 }}>{r.categories.join(" + ")}</span>
                    {r.strikes > 0 && <span className="pill review">strikes: {r.strikes}</span>}
                    {r.restrict_user && <span className="pill review">Restrict user</span>}
                    {r.report_required && <span className="pill cc-badge">Possible cybercrime</span>}
                    {r.incident_id && <span className="muted" style={{ fontSize: 13 }}>incident #{r.incident_id}</span>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
