import pandas as pd

def scan(path):
    cols = list(pd.read_csv(path, nrows=0).columns)
    text = next((c for c in cols if "text" in c.lower() or "comment" in c.lower()), cols[0])
    print("\n==", path, "| columns:", cols, "| text column:", text)
    n = nh = ne = 0
    tot, hey, exact = {}, {}, {}
    samples = []
    for ch in pd.read_csv(path, chunksize=50000, encoding_errors="replace"):
        t = ch[text].astype(str).str.lower()
        mh = t.str.contains(r"\bhey\b", regex=True)
        me = t.str.strip() == "hey"
        n += len(ch); nh += int(mh.sum()); ne += int(me.sum())
        num = ch.select_dtypes("number")
        for c in num.columns:
            tot[c] = tot.get(c, 0) + float(num[c].sum())
            hey[c] = hey.get(c, 0) + float(num.loc[mh, c].sum())
            exact[c] = exact.get(c, 0) + float(num.loc[me, c].sum())
        if len(samples) < 4 and mh.any():
            samples += ch.loc[mh, text].astype(str).str.slice(0, 80).head(4 - len(samples)).tolist()
    print("rows:", n, "| containing 'hey':", nh, "| exactly 'hey':", ne)
    for c in tot:
        line = f"  {c}: overall {tot[c]/n:.3f}"
        if nh: line += f" | with hey {hey[c]/nh:.3f}"
        if ne: line += f" | exactly hey {exact[c]/ne:.3f}"
        print(line)
    print("sample rows with hey:", samples)

scan("data/jigsaw_train.csv")
scan("data/sexual_dataset.csv")
