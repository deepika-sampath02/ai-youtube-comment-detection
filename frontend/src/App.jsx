import { useRef, useState } from "react";
import "./Tester.css";

const SEV = {
  NONE: { label: "Looks safe", cls: "ok" },
  LOW: { label: "Low risk", cls: "low" },
  MEDIUM: { label: "Needs attention", cls: "med" },
  HIGH: { label: "Harmful", cls: "high" },
  CRITICAL: { label: "Severe", cls: "crit" },
};

const EXAMPLES = [
  "Where did you get this dress from?",
  "You are an idiot",
  "I know where you live",
  "Can you send me some nude photos",
];

const STEPS = [
  ["Analyze", "The model reads the comment and scores it for offensive language, harassment, threats and sexual content."],
  ["Decide", "A policy turns the scores into an action: allow, warn or remove, and counts strikes for repeat users."],
  ["Human review", "Removed comments become incidents. A person confirms or dismisses each one, and files any report themselves."],
];

function Art() {
  return (
    <svg className="tt-art" viewBox="0 0 460 380" role="img" aria-label="A shield checking a feed of comments">
      <rect x="30" y="30" width="330" height="320" rx="24" fill="#fff" stroke="#DCE3EE" strokeWidth="2" />
      <circle cx="62" cy="64" r="10" fill="#C9D4E5" />
      <rect x="82" y="58" width="96" height="12" rx="6" fill="#C9D4E5" />

      <rect x="52" y="96" width="286" height="62" rx="14" fill="#E8F7F4" />
      <circle cx="80" cy="127" r="14" fill="#0E9F8E" />
      <rect x="104" y="112" width="150" height="9" rx="4.5" fill="#9FD8D0" />
      <rect x="104" y="130" width="100" height="9" rx="4.5" fill="#C5E8E3" />
      <circle cx="314" cy="127" r="12" fill="#0E9F8E" />
      <path d="M308 127 L312.5 131.5 L320.5 122.5" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />

      <rect x="52" y="172" width="286" height="62" rx="14" fill="#FFF4DF" />
      <circle cx="80" cy="203" r="14" fill="#F5A524" />
      <rect x="104" y="188" width="140" height="9" rx="4.5" fill="#F3D08F" />
      <rect x="104" y="206" width="110" height="9" rx="4.5" fill="#F8E3B9" />
      <circle cx="314" cy="203" r="12" fill="#F5A524" />
      <rect x="312.6" y="195.5" width="2.8" height="9" rx="1.4" fill="#fff" />
      <circle cx="314" cy="209.5" r="1.7" fill="#fff" />

      <rect x="52" y="248" width="286" height="62" rx="14" fill="#FDECEC" />
      <circle cx="80" cy="279" r="14" fill="#E5484D" />
      <rect x="104" y="264" width="158" height="9" rx="4.5" fill="#F0A9AB" />
      <rect x="104" y="282" width="84" height="9" rx="4.5" fill="#F6CACB" />
      <circle cx="314" cy="279" r="12" fill="#E5484D" />
      <path d="M309 274 L319 284 M319 274 L309 284" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />

      <rect className="tt-scan" x="40" y="90" width="310" height="3" rx="1.5" fill="#0E9F8E" opacity="0.55" />

      <g transform="translate(284 118) scale(2.6)">
        <path d="M32 3 L57 11 V30 C57 46 46 57 32 61 C18 57 7 46 7 30 V11 Z" fill="#0E9F8E" stroke="#fff" strokeWidth="2.2" />
        <rect x="19" y="19" width="26" height="17" rx="5" fill="#fff" />
        <path d="M25 35 L25 43 L33 35 Z" fill="#fff" />
        <path d="M26 27.5 L30.5 32 L38.5 23.5" fill="none" stroke="#0E9F8E" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

export default function App() {
  const [comment, setComment] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const box = useRef(null);

  const check = async () => {
    if (!comment.trim() || loading) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch("/api/moderate/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setResult(data);
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);
    }
    setLoading(false);
  };

  const sev = result ? SEV[result.severity] || SEV.NONE : null;
  const flags = result ? [
    result.needs_review && "Needs human review",
    result.escalate && "Escalated",
    result.report_required && "Possible cybercrime",
    result.restrict_user && "Restrict user advised",
    result.strikes > 0 && `Strikes: ${result.strikes}`,
    result.incident_id && `Incident #${result.incident_id} opened`,
  ].filter(Boolean) : [];

  return (
    <div className="tt-page">
      <div className="tt-inner">
        <section className="tt-hero">
          <div>
            <h1 className="tt-h1">Catch harmful comments before they reach anyone</h1>
            <p className="tt-sub">
              Paste a comment and see how it would be handled: what kind of content it is,
              how severe it is, and what a moderator should do next.
            </p>
            <div className="tt-trust">
              <span>Offensive language</span>
              <span>Harassment</span>
              <span>Threats</span>
              <span>Sexual content</span>
            </div>
          </div>
          <Art />
        </section>

        <section className="tt-panel">
          <h2 className="tt-h2">Try a comment</h2>
          <div className="tt-examples">
            <span className="tt-hint">Start from an example:</span>
            {EXAMPLES.map((ex) => (
              <button key={ex} type="button" className="tt-chip"
                onClick={() => { setComment(ex); setResult(null); setError(""); box.current && box.current.focus(); }}>
                {ex}
              </button>
            ))}
          </div>
          <textarea ref={box} className="tt-input" rows={4} maxLength={1000}
            placeholder="Type or paste a comment..." value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check(); }} />
          <div className="tt-actions">
            <button className="tt-btn" onClick={check} disabled={loading || !comment.trim()}>
              {loading ? "Checking..." : "Analyze comment"}
            </button>
            <span className="tt-count">{comment.length} / 1000 - Ctrl+Enter to analyze</span>
          </div>
          {error && <div className="tt-error" role="alert">{error}</div>}

          {result && (
            <div className={`tt-result sev-${sev.cls}`} aria-live="polite">
              <div className="tt-verdict">
                <div>
                  <div className="tt-sevlabel">{sev.label}</div>
                  <h3>{result.categories.join(" + ")}</h3>
                </div>
                <div className="tt-tags">
                  <span className="tt-pill strong">Severity: {result.severity}</span>
                  <span className="tt-pill">Action: {result.action}</span>
                </div>
              </div>
              <div className="tt-body">
                {flags.length > 0 && (
                  <div className="tt-flags">{flags.map((f) => <span key={f} className="tt-flag">{f}</span>)}</div>
                )}
                <div className="tt-scores">
                  {Object.entries(result.scores).map(([k, v]) => (
                    <div key={k} className="tt-score">
                      <div className="tt-score-top">
                        <span>{k.charAt(0).toUpperCase() + k.slice(1)}</span>
                        <span>{(v * 100).toFixed(1)}%</span>
                      </div>
                      <div className="tt-bar"><div className="tt-fill" style={{ width: `${Math.min(100, v * 100)}%` }} /></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="tt-how">
          <h2 className="tt-h2">How a comment is handled</h2>
          <div className="tt-steps">
            {STEPS.map(([title, text], i) => (
              <div key={title} className="tt-step">
                <div className="tt-num">{i + 1}</div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <p className="tt-foot">
          Results are a triage aid. A person confirms every incident, and nothing is sent to any authority automatically.
        </p>
      </div>
    </div>
  );
}
