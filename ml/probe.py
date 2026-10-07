import os, sys
sys.path.insert(0, "ml")
from moderator import Moderator
m = Moderator()
tests = ["hey", "hi", "hii", "hey hi", "hey hii", "hello", "heyyy", "hii there", "good morning", "thanks", "ok", "nice", "lol", "hey hottie"]
for t in tests:
    r = m.analyze(t)
    top = sorted(r["scores"].items(), key=lambda kv: -kv[1])[:2]
    print(f'{t!r:14} -> {r["severity"]:7} {r["categories"]}  top: ' + ", ".join(f"{k}={v:.2f}" for k, v in top))
