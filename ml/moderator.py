"""Combines both models into one final decision."""
import os, re, sys, joblib

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import clean_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THRESHOLD = 0.5

THREAT_PATTERNS = [
    r"\b(i|we|i'll|i will|i'm going to|im going to|gonna|going to)\b.{0,25}\b(kill|hurt|murder|stab|shoot|beat|find|destroy|rape|burn)\b.{0,15}\b(you|u|ya|your family|him|her|them)\b",
    r"\b(you|u)\b.{0,10}\b(will|gonna|are going to|better)\b.{0,15}\b(die|pay|regret|suffer)\b",
    r"\bi('ll| will) (find|get|hunt) (you|u)\b",
    r"\b(kill|murder|shoot|stab) (you|u|yourself)\b",
    r"\byou('re| are) (dead|a dead man)\b",
]
BENIGN_PATTERN = re.compile(
    r"\b(kill(ing|ed)?|crush(ing|ed)?|slay(ing|ed)?|murder(ing|ed)?|destroy(ing|ed)?)\s+"
    r"(it|this|that|the|my|today|tonight)\b.{0,20}\b(workout|exam|test|interview|game|presentation|gym|set|look|vibe|day)\b"
    r"|\bkilling it\b|\bslay(s|ed|ing)?\b", re.I)

SEXUAL_PATTERNS = [
    r"\bnudes?\b", r"\bdick\s*pics?\b", r"\bsext(ing)?\b", r"\bhorny\b",
    r"\bporn\b", r"\b(send|show)\b.{0,12}\b(boobs|tits|pussy)\b",
    r"\blet'?s\s+(have\s+sex|hook\s*up|fuck)\b",
]


class Moderator:
    def __init__(self):
        tox = joblib.load(os.path.join(ROOT, "models", "toxicity_model.joblib"))
        self.tox_model, self.labels = tox["model"], tox["labels"]
        self.thresholds = tox.get("thresholds", {l: THRESHOLD for l in self.labels})
        sex_path = os.path.join(ROOT, "models", "sexual_model.joblib")
        self.sex_model = joblib.load(sex_path) if os.path.exists(sex_path) else None

    @staticmethod
    def _rule_threat(comment: str) -> bool:
        t = comment.lower()
        return any(re.search(p, t) for p in THREAT_PATTERNS)

    def analyze(self, comment: str) -> dict:
        text = clean_text(comment)
        tox_probs = dict(zip(self.labels, self.tox_model.predict_proba([text])[0]))
        sexual = float(self.sex_model.predict_proba([text])[0][1]) if self.sex_model else 0.0

        th = self.thresholds
        categories = []
        if tox_probs["threat"] >= th["threat"]:
            categories.append("Threat")
        if sexual >= THRESHOLD:
            categories.append("Sexual / 18+")
        if (tox_probs["severe_toxic"] >= th["severe_toxic"] and tox_probs["obscene"] >= th["obscene"]) \
                or tox_probs["identity_hate"] >= th["identity_hate"]:
            categories.append("Abusive")
        if tox_probs["insult"] >= th["insult"]:
            categories.append("Harassment")
        if tox_probs["toxic"] >= th["toxic"] or tox_probs["obscene"] >= th["obscene"]:
            categories.append("Offensive")

        # Rule layer: the model is weak on threats, so catch clear threat phrases
        if self._rule_threat(comment):
            if "Threat" not in categories:
                categories.insert(0, "Threat")
            tox_probs["threat"] = max(float(tox_probs["threat"]), 0.9)
        
        # Rule layer: sexual solicitation the model misses
        if any(re.search(p, comment.lower()) for p in SEXUAL_PATTERNS):
            if "Sexual / 18+" not in categories:
                categories.append("Sexual / 18+")
            sexual = max(sexual, 0.9)

        # Rule layer: harmless slang like "kill this workout"
        if BENIGN_PATTERN.search(comment) and not self._rule_threat(comment):
            categories = [c for c in categories if c not in ("Threat", "Offensive")]
            tox_probs["threat"] = min(float(tox_probs["threat"]), 0.1)
            tox_probs["toxic"] = min(float(tox_probs["toxic"]), 0.3)

        if not categories:
            categories = ["Normal"]

        top = max(max(tox_probs.values()), sexual)
        toxic_flag = any(c in categories for c in ("Threat", "Abusive", "Harassment", "Offensive"))
        if categories == ["Normal"]:
            severity = "NONE"
        elif toxic_flag and "Sexual / 18+" in categories:
            severity = "CRITICAL"
        elif "Threat" in categories or top >= 0.85:
            severity = "HIGH"
        elif top >= 0.65:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        return {
            "comment": comment,
            "categories": categories,
            "severity": severity,
            "needs_review": severity in ("HIGH", "CRITICAL"),
            "scores": {**{k: round(float(v), 4) for k, v in tox_probs.items()},
                       "sexual": round(sexual, 4)},
        }


if __name__ == "__main__":
    m = Moderator()
    tests = [
        "Have a great day!",
        "you are an idiot",
        "I will find you and hurt you",
        "I'm going to kill this workout today",
        "you will regret this",
        "send nudes",
    ]
    for c in tests:
        r = m.analyze(c)
        print(f"{c!r:45} -> {r['categories']} | {r['severity']}")
