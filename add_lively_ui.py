"""add_lively_ui.py

Adds to every page: an illustrated banner at the top, smooth page transitions, hover/press
animations on cards and buttons, and staggered fade-in of page sections.
New files: frontend/src/PageHero.jsx, frontend/src/lively.css
Edited file: frontend/src/Root.jsx (backup: Root.jsx.bak3)
Put this file in the project's main folder and run:  python add_lively_ui.py
Changes nothing if any check fails.
"""
import os
import shutil

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


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        fail("could not find (exactly once): " + what)
    return text.replace(old, new, 1)


P_ROOT = path("frontend", "src", "Root.jsx")
P_HERO = path("frontend", "src", "PageHero.jsx")
P_CSS = path("frontend", "src", "lively.css")

if not os.path.exists(P_ROOT):
    fail("file not found: " + P_ROOT + " (is this script in the project's main folder?)")
r = read(P_ROOT)
if "PageHero" in r or os.path.exists(P_HERO):
    fail("the lively UI is already installed.")

r = replace_once(r, 'import "./Root.css";',
                 'import PageHero from "./PageHero.jsx";\nimport "./Root.css";\nimport "./lively.css";',
                 "Root.css import")
r = replace_once(r, '      {tab === "dash" && <Dashboard go={setTab} />}\n',
                 '      <PageHero tab={tab} />\n      <div key={tab} className="page-fade">\n'
                 '      {tab === "dash" && <Dashboard go={setTab} />}\n',
                 "dashboard render line")
r = replace_once(r, '      {tab === "history" && <History />}\n    </div>',
                 '      {tab === "history" && <History />}\n      </div>\n    </div>',
                 "history render line")

HERO_JSX = r'''const Bubble = ({ x, y, w, c, d }) => (
  <g className={"float " + (d || "")}>
    <rect x={x} y={y} width={w} height="26" rx="13" fill="#fff" opacity=".92" />
    <circle cx={x + 16} cy={y + 13} r="5" fill={c} />
    <rect x={x + 26} y={y + 9} width={w - 42} height="8" rx="4" fill={c} opacity=".45" />
  </g>
);

const Shield = ({ x, y, mark }) => (
  <g className="float d2">
    <path d={`M${x} ${y} l22 8 v16 c0 10-9 17-22 20 c-13-3-22-10-22-20 v-16 z`} fill="#fff" />
    {mark === "!" ? (
      <g fill="#E5484D"><rect x={x - 2.5} y={y + 12} width="5" height="14" rx="2.5" /><circle cx={x} cy={y + 33} r="3" /></g>
    ) : (
      <polyline points={`${x - 9},${y + 24} ${x - 2},${y + 31} ${x + 11},${y + 15}`} fill="none" stroke="#0E9F8E" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    )}
  </g>
);

const ART = {
  yt: (
    <>
      <rect x="14" y="28" width="116" height="74" rx="12" fill="#fff" opacity=".2" />
      <polygon points="56,50 56,82 86,66" fill="#fff" />
      <Bubble x={118} y={14} w={86} c="#0E9F8E" />
      <Bubble x={138} y={48} w={72} c="#E5484D" d="d3" />
      <Shield x={170} y={84} />
    </>
  ),
  dash: (
    <>
      {[[22, 70], [52, 48], [82, 60], [112, 30], [142, 40]].map(([x, y]) => (
        <rect key={x} className="grow" x={x} y={y} width="20" height={108 - y} rx="5" fill="#fff" opacity=".85" />
      ))}
      <polyline points="30,62 62,40 92,52 122,22 152,32" fill="none" stroke="#FFD166" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <Shield x={186} y={46} />
    </>
  ),
  tester: (
    <>
      <Bubble x={14} y={20} w={110} c="#0E9F8E" />
      <Bubble x={40} y={58} w={96} c="#E5484D" d="d3" />
      <g className="float d2">
        <circle cx="170" cy="56" r="26" fill="#fff" opacity=".25" stroke="#fff" strokeWidth="6" />
        <line x1="190" y1="76" x2="208" y2="96" stroke="#fff" strokeWidth="8" strokeLinecap="round" />
      </g>
    </>
  ),
  incidents: (
    <>
      <rect x="22" y="22" width="92" height="84" rx="10" fill="#fff" opacity=".2" />
      {[38, 56, 74].map((y) => <rect key={y} x="34" y={y} width="68" height="8" rx="4" fill="#fff" opacity=".8" />)}
      <Shield x={166} y={34} mark="!" />
    </>
  ),
  history: (
    <>
      <g className="float">
        <circle cx="70" cy="62" r="40" fill="#fff" opacity=".22" stroke="#fff" strokeWidth="6" />
        <polyline points="70,38 70,62 88,72" fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      {[30, 54, 78].map((y) => <rect key={y} x="130" y={y} width="76" height="14" rx="7" fill="#fff" opacity=".85" />)}
    </>
  ),
};

const INFO = {
  yt: ["YouTube Analyzer", "Paste a video link and the AI scans its newest comments for harmful content."],
  dash: ["Security Overview", "A live view of what was analyzed, flagged and waiting for a human decision."],
  tester: ["Comment Tester", "Type any comment and see how the AI would label it."],
  incidents: ["Incident Review", "The AI flags. A person decides. Reports are prepared here, never sent automatically."],
  history: ["Analysis History", "Every comment the system has looked at, with its label and action."],
};

export default function PageHero({ tab }) {
  const info = INFO[tab];
  if (!info) return null;
  return (
    <div className="wrap hero-wrap">
      <div className="hero" key={tab}>
        <div className="hero-text">
          <h1>{info[0]}</h1>
          <p>{info[1]}</p>
        </div>
        <svg className="hero-art" viewBox="0 0 220 130" aria-hidden="true">{ART[tab]}</svg>
      </div>
    </div>
  );
}
'''

LIVELY_CSS = '''/* Added by add_lively_ui.py */
.hero-wrap { padding-bottom: 0 !important; }
.hero { display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 18px 26px; border-radius: 16px; color: #fff; overflow: hidden;
  background: linear-gradient(120deg, #0b2a45 0%, #0b5c68 55%, #0E9F8E 100%);
  box-shadow: 0 10px 28px rgba(11, 42, 69, .22); animation: pgin .5s ease backwards; }
.hero h1 { margin: 0 0 6px; font-size: 24px; }
.hero p { margin: 0; opacity: .88; max-width: 520px; line-height: 1.45; }
.hero-art { width: 220px; height: 130px; flex-shrink: 0; }
.float { animation: flt 3.2s ease-in-out infinite; }
.float.d2 { animation-delay: .6s; }
.float.d3 { animation-delay: 1.2s; }
.grow { transform-box: fill-box; transform-origin: bottom; animation: grw .9s ease backwards; }
@keyframes flt { 50% { transform: translateY(-6px); } }
@keyframes grw { from { transform: scaleY(0); } }

.page-fade { animation: pgin .45s ease backwards; }
.page-fade .wrap > * { animation: pgin .5s ease backwards; }
.page-fade .wrap > *:nth-child(2) { animation-delay: .06s; }
.page-fade .wrap > *:nth-child(3) { animation-delay: .12s; }
.page-fade .wrap > *:nth-child(4) { animation-delay: .18s; }
.page-fade .wrap > *:nth-child(5) { animation-delay: .24s; }
.page-fade .wrap > *:nth-child(n+6) { animation-delay: .3s; }
@keyframes pgin { from { opacity: 0; transform: translateY(12px); } }

.card, .dstat, .inc, .feed-row, .yt-item { transition: transform .2s, box-shadow .2s, border-color .2s; }
.card:hover, .dstat:hover, .inc:hover { transform: translateY(-2px); box-shadow: 0 10px 26px rgba(11, 42, 69, .14); }
.feed-row:hover { transform: translateX(3px); }
.btn, .ghost, .tabs button { transition: transform .15s, box-shadow .2s, background .2s, color .2s; }
.btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(14, 159, 142, .35); }
.btn:active:not(:disabled), .ghost:active { transform: scale(.97); }
.ghost:hover, .tabs button:hover { transform: translateY(-1px); }
.pill { transition: transform .15s; }
.pill:hover { transform: scale(1.07); }

@media (max-width: 700px) { .hero-art { display: none; } .hero { padding: 16px 18px; } }
@media (prefers-reduced-motion: reduce) {
  .hero, .page-fade, .page-fade .wrap > *, .float, .grow { animation: none !important; }
  .card, .dstat, .inc, .feed-row, .btn, .ghost, .tabs button, .pill { transition: none !important; }
}
'''

shutil.copyfile(P_ROOT, P_ROOT + ".bak3")
write(P_HERO, HERO_JSX)
write(P_CSS, LIVELY_CSS)
write(P_ROOT, r)
print("lively ui patched")
