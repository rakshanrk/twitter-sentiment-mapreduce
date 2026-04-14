import sys

positive = ['good','great','happy','love','awesome']
negative = ['bad','hate','sad','worst','terrible']

first_line = True
for line in sys.stdin:
    if first_line:
        first_line = False
        continue  # skip CSV header
    words = line.lower().split()
    pos = sum(1 for w in words if w in positive)
    neg = sum(1 for w in words if w in negative)
    if pos > neg:
        print("positive\t1")
    elif neg > pos:
        print("negative\t1")
    else:
        print("neutral\t1")
