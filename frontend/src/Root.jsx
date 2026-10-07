import { useState } from "react";
import Dashboard from "./Dashboard.jsx";
import Feed from "./Feed.jsx";
import Instagram from "./Instagram.jsx";
import YouTube from "./YouTube.jsx";
import App from "./App.jsx";
import Simulator from "./Simulator.jsx";
import Incidents from "./Incidents.jsx";
import History from "./History.jsx";
import Logo from "./Logo.jsx";
import PageHero from "./PageHero.jsx";
import "./Root.css";
import "./lively.css";

// Feed, Instagram and Social Simulator are hidden from the menu.
// To bring one back, add its line to this list again:
//   ["feed", "Feed"], ["ig", "Instagram"], ["sim", "Social Simulator"]
const TABS = [
  ["yt", "YouTube"],
  ["dash", "Dashboard"],
  ["tester", "Comment Tester"],
  ["incidents", "Incidents"],
  ["history", "History"],
];

export default function Root() {
  const [tab, setTab] = useState("yt");
  return (
    <div>
      <div className="tabs">
        <div className="brand"><Logo size={30} /><span>SafeComment AI</span></div>
        {TABS.map(([k, label]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      <PageHero tab={tab} />
      <div key={tab} className="page-fade">
      {tab === "dash" && <Dashboard go={setTab} />}
      {tab === "feed" && <Feed />}
      {tab === "ig" && <Instagram />}
      {tab === "yt" && <YouTube />}
      {tab === "tester" && <App />}
      {tab === "sim" && <Simulator />}
      {tab === "incidents" && <Incidents />}
      {tab === "history" && <History />}
      </div>
    </div>
  );
}
