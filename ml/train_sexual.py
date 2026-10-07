import joblib, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import make_pipeline
from preprocess import clean_text

df = pd.read_csv("data/sexual_dataset.csv").dropna()
df["text"] = df["comment"].astype(str).map(clean_text)
X_train, X_val, y_train, y_val = train_test_split(
    df["text"], df["sexual"], test_size=0.15, random_state=42, stratify=df["sexual"])

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), max_features=100_000, min_df=2, sublinear_tf=True),
    LogisticRegression(C=4, class_weight="balanced", max_iter=300),
)
model.fit(X_train, y_train)

p = model.predict_proba(X_val)[:, 1]
print("ROC-AUC:", round(roc_auc_score(y_val, p), 4))
print(classification_report(y_val, p >= 0.5, target_names=["not_sexual", "sexual"]))

joblib.dump(model, "models/sexual_model.joblib")
print("Saved models/sexual_model.joblib")
