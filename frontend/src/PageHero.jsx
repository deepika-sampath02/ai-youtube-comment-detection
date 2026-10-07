const Bubble = ({ x, y, w, c, d }) => (
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
