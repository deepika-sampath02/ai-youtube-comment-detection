"""Bulk-test the moderator. Run from project root: python ml/test_moderator.py"""
import os, sys
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, os.path.dirname(__file__))
from moderator import Moderator

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/test_comments.csv"
df = pd.read_csv(SRC, sep="|", header=None,
                 names=["expected", "comment"], quoting=3, encoding="utf-8-sig")
df = df.dropna()
df["expected"] = df["expected"].str.strip().str.upper()
df = df[df["expected"] != "LABEL"].copy()
df["expected"] = df["expected"].replace({"NORMAL": "SAFE", "ABUSIVE": "OFFENSIVE", "HARASSMENT": "OFFENSIVE"})
df["comment"] = df["comment"].str.strip()
m = Moderator()


def simplify(cats):
    if "Threat" in cats:
        return "THREAT"
    if "Sexual / 18+" in cats:
        return "SEXUAL"
    if cats == ["Normal"]:
        return "SAFE"
    return "OFFENSIVE"


rows = []
for exp, c in zip(df["expected"], df["comment"]):
    r = m.analyze(c)
    rows.append({"expected": exp, "predicted": simplify(r["categories"]),
                 "severity": r["severity"], "categories": " + ".join(r["categories"]), "comment": c, "sexual": round(r["scores"]["sexual"], 2)})
res = pd.DataFrame(rows)
res.to_csv(SRC.replace(".csv", "_results.csv"), index=False)

labels = ["SAFE", "OFFENSIVE", "THREAT", "SEXUAL"]
acc = (res["expected"] == res["predicted"]).mean()
print(f"\nOverall accuracy: {acc:.1%}  ({len(res)} comments)\n")
print(classification_report(res["expected"], res["predicted"], labels=labels, zero_division=0))
print("Confusion matrix (rows = expected, columns = predicted):")
print(pd.DataFrame(confusion_matrix(res["expected"], res["predicted"], labels=labels),
                   index=labels, columns=labels), "\n")

print("Severity given to each expected class:")
print(pd.crosstab(res["expected"], res["severity"]), "\n")

bad = res[res["expected"] != res["predicted"]]
print(f"FAILURES ({len(bad)}):")
for _, b in bad.iterrows():
    print(f"  expected {b['expected']:9} got {b['predicted']:9} | s={b['sexual']} | {b['comment']}")
