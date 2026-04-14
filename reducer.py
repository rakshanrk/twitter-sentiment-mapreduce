import sys

counts = {}

for line in sys.stdin:
    line = line.strip()
    if '\t' not in line:
        continue  # skip malformed lines
    key, value = line.split("\t")
    counts[key] = counts.get(key, 0) + int(value)

for key in counts:
    print("{}\t{}".format(key, counts[key]))