"""
patch_menu.py - hides Feed, Instagram and Social Simulator tabs,
puts YouTube first and makes it the page the app opens on,
and points the Dashboard buttons to YouTube instead of the simulator.

Run from the project's main folder (the one that contains "frontend"):
    python patch_menu.py

Backups are saved next to each file as Root.jsx.bak and Dashboard.jsx.bak.
To undo: delete the edited file and rename the .bak file back.
"""
import shutil
import sys
from pathlib import Path

SRC = Path("frontend") / "src"
ROOT = SRC / "Root.jsx"
DASH = SRC / "Dashboard.jsx"


def stop(reason):
    print("STOPPED:", reason)
    sys.exit(1)


def read(p):
    if not p.exists():
        stop(f"{p} not found. Run this from the folder that contains 'frontend'.")
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        stop(f"expected 1 match for [{label}] but found {n}. No files were changed.")
    return text.replace(old, new)


root = read(ROOT)
dash = read(DASH)

# ---- Root.jsx ----
old_tabs = '''const TABS = [
  ["dash", "Dashboard"],
  ["feed", "Feed"],
  ["ig", "Instagram"],
  ["yt", "YouTube"],
  ["tester", "Comment Tester"],
  ["sim", "Social Simulator"],
  ["incidents", "Incidents"],
  ["history", "History"],
];'''
new_tabs = '''// Feed, Instagram and Social Simulator are hidden from the menu.
// To bring one back, add its line to this list again:
//   ["feed", "Feed"], ["ig", "Instagram"], ["sim", "Social Simulator"]
const TABS = [
  ["yt", "YouTube"],
  ["dash", "Dashboard"],
  ["tester", "Comment Tester"],
  ["incidents", "Incidents"],
  ["history", "History"],
];'''
root = replace_once(root, old_tabs, new_tabs, "TABS list")
root = replace_once(root, 'useState("dash")', 'useState("yt")', "default tab")

# ---- Dashboard.jsx ----
dash = replace_once(
    dash,
    "Run the fake feed to see this dashboard fill with real results.",
    "Fetch comments from a YouTube video to see this dashboard fill with real results.",
    "empty text",
)
dash = replace_once(
    dash,
    '<button className="btn" onClick={() => go("sim")}>Open the Social Simulator</button>',
    '<button className="btn" onClick={() => go("yt")}>Open YouTube</button>',
    "empty button",
)
dash = replace_once(
    dash,
    '<button className="ghost" onClick={() => go("sim")}>Run the simulator</button>',
    '<button className="ghost" onClick={() => go("yt")}>Fetch YouTube comments</button>',
    "quick button",
)

# ---- backups, then write ----
for p in (ROOT, DASH):
    shutil.copyfile(p, str(p) + ".bak")

with open(ROOT, "w", encoding="utf-8") as f:
    f.write(root)
with open(DASH, "w", encoding="utf-8") as f:
    f.write(dash)

print("menu patched")
