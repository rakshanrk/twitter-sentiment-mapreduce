import pandas as pd

df = pd.read_csv("training.1600000.processed.noemoticon.csv",
                  encoding="latin-1", header=None)
df.columns = ["sentiment","id","date","query","user","text"]

# Take 500 from start (negative) + 500 from end (positive) for balance
df = pd.concat([df.head(500), df.tail(500)])[["text"]]
df.to_csv("tweets.csv", index=False)
print("Done!")