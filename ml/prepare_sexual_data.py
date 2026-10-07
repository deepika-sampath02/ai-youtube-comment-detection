import pandas as pd

df = pd.read_csv("data/jigsaw_train.csv", usecols=["comment_text", "sexual_explicit"])
df = df.dropna()

pos = df[df["sexual_explicit"] >= 0.5]
neg = df[df["sexual_explicit"] == 0].sample(n=min(len(pos) * 4, len(df)), random_state=42)

out = pd.concat([
    pd.DataFrame({"comment": pos["comment_text"], "sexual": 1}),
    pd.DataFrame({"comment": neg["comment_text"], "sexual": 0}),
]).sample(frac=1, random_state=42)

out.to_csv("data/sexual_dataset.csv", index=False)
print(f"Saved {len(out)} rows ({len(pos)} sexual / {len(neg)} not sexual)")
