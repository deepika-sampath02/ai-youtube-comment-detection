import { useEffect, useState } from "react";
import "./Feed.css";

const USERS = ["you", "maya_k", "ravi_22", "nina_b", "dev_sam", "kiran_p", "troll_99", "anon_x7"];
const SEV_LABEL = { LOW: "low risk", MEDIUM: "medium risk", HIGH: "high risk", CRITICAL: "severe" };

function hue(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }

function ago(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min";
  if (s < 86400) return Math.floor(s / 3600) + " h";
  return Math.floor(s / 86400) + " d";
}

function Avatar({ name, size = 36 }) {
  return (
    <div className="av" style={{ width: size, height: size, fontSize: size * 0.42, background: `hsl(${hue(name)} 55% 42%)` }}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

function Heart({ on }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 2.7 5 6 5c2 0 3.4 1.1 4.2 2.4h.1C11.1 6.1 12.5 5 14.5 5c3.3 0 5.1 3.4 3.6 6.8C19.5 16.4 12 21 12 21z"
        fill={on ? "#E5484D" : "none"} stroke={on ? "#E5484D" : "#0B1F3A"} strokeWidth="1.8" strokeLinejoin="round" transform="translate(0 -1)" />
    </svg>
  );
}

export default function Feed() {
  const [user, setUser] = useState("you");
  const [posts, setPosts] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [pending, setPending] = useState({});
  const [notes, setNotes] = useState({});
  const [liked, setLiked] = useState({});
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const [reported, setReported] = useState({});

  const fail = (e) => setError(e.message === "Failed to fetch" ? "Cannot reach the server. Is the Django backend running?" : e.message);

  const load = async () => {
    try {
      const res = await fetch("/api/posts/?viewer=" + encodeURIComponent(user));
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setPosts(data.results); setError("");
    } catch (e) { fail(e); }
  };
  useEffect(() => { load(); }, [user]);

  const send = async (post, confirmId) => {
    const text = (drafts[post.id] || "").trim();
    if (!text) return;
    setBusy(post.id); setError("");
    try {
      const payload = { user_id: user, comment: text };
      if (confirmId) payload.confirm_analysis_id = confirmId;
      const res = await fetch(`/api/posts/${post.id}/comments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      if (data.outcome === "confirm") {
        setPending((p) => ({ ...p, [post.id]: { id: data.analysis_id, categories: data.categories, severity: data.severity } }));
        setNotes((n) => ({ ...n, [post.id]: "" }));
      } else {
        setPending((p) => ({ ...p, [post.id]: null }));
        setDrafts((d) => ({ ...d, [post.id]: "" }));
        setNotes((n) => ({ ...n, [post.id]: data.outcome === "held" ? (data.restricted ? "restricted" : "held") : "" }));
        await load();
      }
    } catch (e) { fail(e); }
    setBusy(null);
  };

  const reportComment = async (id) => {
    try {
      const res = await fetch(`/api/comments/${id}/report/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user, reason: "reported by user" }),
      });
      const data = await res.json();
      if (!res.ok && !String(data.error || "").includes("already")) throw new Error(data.error || "Report failed");
      setReported((r) => ({ ...r, [id]: true }));
    } catch (e) { fail(e); }
  };

  const edit = (post, value) => {
    setDrafts((d) => ({ ...d, [post.id]: value }));
    setPending((p) => ({ ...p, [post.id]: null }));
    setNotes((n) => ({ ...n, [post.id]: "" }));
  };

  return (
    <div className="wrap">
      <div>
        <h2 style={{ margin: "0 0 6px" }}>SafeSocial feed</h2>
        <p className="muted" style={{ margin: 0 }}>
          A small social app with SafeComment AI built in. Every comment is checked before anyone else can see it:
          safe ones appear, hurtful ones ask you to confirm, and serious ones wait for a human moderator.
        </p>
      </div>

      <div className="card filters">
        <label className="fd-as" htmlFor="fd-user">Posting as</label>
        <select id="fd-user" value={user} onChange={(e) => setUser(e.target.value)}>
          {USERS.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        <Avatar name={user} size={30} />
        <button className="ghost" onClick={load}>Refresh</button>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="fd-feed">
        {posts.map((post) => {
          const isLiked = !!liked[post.id];
          const pend = pending[post.id];
          const note = notes[post.id];
          return (
            <article key={post.id} className="fd-post">
              <header className="fd-head">
                <Avatar name={post.author} />
                <div>
                  <div className="fd-author">{post.author}</div>
                  <div className="muted" style={{ fontSize: 13 }}>{ago(post.created_at)}</div>
                </div>
              </header>

              <div className="fd-img" style={{ background: `linear-gradient(135deg, ${post.color}, #0B1F3A)` }}>
                <span>{post.caption}</span>
              </div>

              <div className="fd-actions">
                <button className="fd-like" aria-pressed={isLiked} aria-label="Like"
                  onClick={() => setLiked((l) => ({ ...l, [post.id]: !l[post.id] }))}>
                  <Heart on={isLiked} />
                </button>
                <span>{post.likes + (isLiked ? 1 : 0)} likes</span>
                <span className="muted">{post.comment_count} comments</span>
              </div>

              <div className="fd-caption"><b>{post.author}</b> {post.caption}</div>

              <div className="fd-comments">
                {post.comments.map((c) => (
                  <div key={c.id} className={`fd-comment ${c.state === "held" ? "held" : ""}`}>
                    <Avatar name={c.user_id} size={26} />
                    <div className="fd-ctext">
                      <b>{c.user_id}</b> {c.text}
                      {c.state === "held" && <span className="pill review" style={{ marginLeft: 8 }}>Under review - only you can see this</span>}
                    </div>
                    {c.state === "published" && c.user_id !== user && (
                      reported[c.id]
                        ? <span className="fd-rep done">Reported</span>
                        : <button className="fd-rep" onClick={() => reportComment(c.id)}>Report</button>
                    )}
                  </div>
                ))}
              </div>

              {pend && (
                <div className="fd-warn" role="alert">
                  <b>This comment may be hurtful.</b>
                  <div>
                    It looks like: {pend.categories.join(" + ")} ({SEV_LABEL[pend.severity] || pend.severity.toLowerCase()}).
                    You can edit it, or post it anyway.
                  </div>
                  <div className="fd-warn-btns">
                    <button className="ghost" onClick={() => setPending((p) => ({ ...p, [post.id]: null }))}>Edit comment</button>
                    <button className="btn" disabled={busy === post.id} onClick={() => send(post, pend.id)}>Post anyway</button>
                  </div>
                </div>
              )}

              {note === "restricted" && (
                <div className="fd-held" role="status">
                  <b>Your account is restricted.</b> After repeated violations, every comment you post is reviewed by a moderator before it appears.
                </div>
              )}
              {note === "held" && (
                <div className="fd-held" role="status">
                  <b>Your comment is being reviewed.</b> A moderator will check it before it appears for other people.
                </div>
              )}

              <div className="fd-box">
                <input placeholder="Add a comment..." value={drafts[post.id] || ""} maxLength={1000}
                  onChange={(e) => edit(post, e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") send(post); }} />
                <button className="fd-send" disabled={busy === post.id || !(drafts[post.id] || "").trim()} onClick={() => send(post)}>
                  {busy === post.id ? "Checking..." : "Post"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
