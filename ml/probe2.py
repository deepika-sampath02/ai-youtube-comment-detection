import pandas as pd
df = pd.read_csv("data/jigsaw_train.csv")
print(list(df.columns))
text = [c for c in df.columns if "comment" in c.lower()][0]
s = df[text].astype(str).str.strip().str.lower()
exact = df[s == "hey"]
print("rows that are exactly 'hey':", len(exact))
if len(exact):
    print(exact.drop(columns=[text]).select_dtypes("number").mean().round(2).to_string())
has = df[s.str.contains(r"\bhey\b", regex=True)]
print("rows containing the word hey:", len(has))
if "obscene" in df.columns:
    print("obscene rate when hey present:", round(has["obscene"].mean(), 3), "| overall:", round(df["obscene"].mean(), 3))
