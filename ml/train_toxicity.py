import joblib, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.pipeline import make_pipeline
from preprocess import clean_text

LABELS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
RENAME = RENAME = {"target": "toxic", "severe_toxicity": "severe_toxic", "identity_attack": "identity_hate"}

df = pd.read_csv("data/jigsaw_train.csv")
print("Columns found:", df.columns.tolist())

df = df.rename(columns=RENAME)
missing = [c for c in ["comment_text"] + LABELS if c not in df.columns]
if missing:
    raise SystemExit(f"Still missing columns: {missing}. Paste the 'Columns found' line to Claude.")

df = df.dropna(subset=["comment_text"] + LABELS)
tox_score = df["toxic"].copy()
for l in LABELS:
    df[l] = (df[l] >= 0.5).astype(int)      # scores -> 0/1
df["severe_toxic"] = (tox_score >= 0.8).astype(int)   # very toxic comments

if len(df) > 400_000:
    df = df.sample(n=400_000, random_state=42)
print("Rows:", len(df))
print(df[LABELS].sum())

df["text"] = df["comment_text"].astype(str).map(clean_text)
X_train, X_val, y_train, y_val = train_test_split(
    df["text"], df[LABELS], test_size=0.15, random_state=42, stratify=df["toxic"])

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), max_features=150_000, min_df=3, sublinear_tf=True),
    OneVsRestClassifier(LogisticRegression(C=4, class_weight="balanced", max_iter=300), n_jobs=-1),
)
print("Training toxicity model...")
model.fit(X_train, y_train)

probs = model.predict_proba(X_val)
for i, label in enumerate(LABELS):
    print(f"{label:15s} ROC-AUC = {roc_auc_score(y_val[label], probs[:, i]):.4f}")
print(classification_report(y_val, probs >= 0.5, target_names=LABELS, zero_division=0))
import numpy as np
from sklearn.metrics import precision_recall_curve

thresholds = {}
for i, label in enumerate(LABELS):
    p, r, t = precision_recall_curve(y_val[label], probs[:, i])
    f1 = 2 * p[:-1] * r[:-1] / (p[:-1] + r[:-1] + 1e-9)
    thresholds[label] = float(max(t[np.argmax(f1)], 0.5))
    print(f"{label:15s} best threshold = {thresholds[label]:.2f}")

pred = np.column_stack([probs[:, i] >= thresholds[l] for i, l in enumerate(LABELS)])
print(classification_report(y_val, pred, target_names=LABELS, zero_division=0))

joblib.dump({"model": model, "labels": LABELS, "thresholds": thresholds},
            "models/toxicity_model.joblib")
print("Saved models/toxicity_model.joblib")