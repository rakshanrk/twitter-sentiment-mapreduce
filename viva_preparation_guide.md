# 🎓 Hadoop MapReduce Viva Preparation Guide

## Table of Contents
1. [Your Project Summary](#your-project-summary)
2. [HDFS Architecture — What to Present](#hdfs-architecture)
3. [MapReduce Paradigm — What to Present](#mapreduce-paradigm)
4. [Daemon Processes — What to Present](#daemon-processes)
5. [Your Code Explained (Line by Line)](#your-code-explained)
6. [How to Demo "MapReduce Reduction" (10MB → 7MB)](#how-to-demo-mapreduction)
7. [Step-by-Step Demo Commands](#step-by-step-demo-commands)
8. [Viva Questions & Answers](#viva-questions--answers)
9. [Project Issues to Fix Before Viva](#project-issues-to-fix)

---

## Your Project Summary

You built a **Twitter Sentiment Analysis** pipeline using Hadoop MapReduce:

| Component | File | Purpose |
|-----------|------|---------|
| Data Prep | `prepare.py` | Extracts 1000 tweets (500 negative + 500 positive) from a 1.6M tweet dataset into `tweets.csv` |
| Mapper | `mapper.py` | Reads each tweet, classifies it as `positive`, `negative`, or `neutral` based on keyword matching |
| Reducer | `reducer.py` | Aggregates counts — totals up how many tweets are positive, negative, neutral |

**Flow:** `tweets.csv` → **Mapper** (classify each tweet) → **Shuffle & Sort** → **Reducer** (count totals) → **Output** (3 lines: positive/negative/neutral counts)

---

## HDFS Architecture

### What is HDFS?
HDFS = **Hadoop Distributed File System**. It's designed to store very large files across multiple machines reliably.

### Key Concepts to Present

```
┌─────────────────────────────────────────────────────┐
│                    HDFS ARCHITECTURE                 │
│                                                      │
│  ┌──────────────┐        ┌──────────────────────┐   │
│  │  NameNode     │        │   DataNode 1          │   │
│  │  (Master)     │◄──────►│   Block A, Block C    │   │
│  │              │        └──────────────────────┘   │
│  │  - Metadata   │                                   │
│  │  - File→Block │        ┌──────────────────────┐   │
│  │    mapping    │◄──────►│   DataNode 2          │   │
│  │  - Namespace  │        │   Block A, Block B    │   │
│  └──────────────┘        └──────────────────────┘   │
│         ▲                                            │
│         │                 ┌──────────────────────┐   │
│         └────────────────►│   DataNode 3          │   │
│                           │   Block B, Block C    │   │
│                           └──────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Points to Explain:

1. **Block Size**: Default block size is **128 MB** (was 64 MB in Hadoop 1.x). Files are split into blocks.
2. **Replication Factor**: Default is **3** — each block is copied to 3 different DataNodes for fault tolerance.
3. **NameNode**: Stores metadata (which file → which blocks → which DataNodes). Single point of contact for clients.
4. **DataNodes**: Store the actual data blocks. Send heartbeat signals to NameNode every 3 seconds.
5. **Secondary NameNode**: NOT a backup! It periodically merges the edit log with the fsimage (checkpoint).

### Example Sentence for Viva:
> "When I upload `tweets.csv` to HDFS, the NameNode breaks it into 128MB blocks, replicates each block to 3 DataNodes, and stores the metadata about where each block lives. If one DataNode fails, the data is still available on the other 2 copies."

---

## MapReduce Paradigm

### What is MapReduce?
A **programming model** for processing large datasets in parallel across a Hadoop cluster.

### The 4 Phases:

```
INPUT DATA                 MAP PHASE              SHUFFLE & SORT           REDUCE PHASE
──────────                 ─────────              ──────────────           ────────────

tweets.csv ──────►  Mapper 1: tweet → positive   ┌─ negative: [1,1,1,1] ──► negative  320
(split into           Mapper 2: tweet → negative  │  neutral:  [1,1,1,1] ──► neutral   280
 chunks)              Mapper 3: tweet → neutral   │  positive: [1,1,1,1] ──► positive  400
                      ...                         └──────────────────────
                      
Each mapper            Key-value pairs are        All values for the      Reducer sums
processes one          emitted as                 SAME KEY are grouped    up all the
line/record            key → value                together automatically  values per key
```

### How Your Code Maps to This:

| Phase | What Happens | Your Code |
|-------|-------------|-----------|
| **Input Split** | Hadoop splits `tweets.csv` into chunks | Automatic by Hadoop |
| **Map** | Each tweet → classified as positive/negative/neutral | `mapper.py` outputs `positive\t1` or `negative\t1` or `neutral\t1` |
| **Shuffle & Sort** | Groups all `positive\t1` together, all `negative\t1` together | Automatic by Hadoop |
| **Reduce** | Counts total for each sentiment | `reducer.py` sums up 1s for each key |

### Key Point About Parallelism:
> "The MapReduce paradigm achieves parallelism by running **multiple mappers simultaneously** on different data splits. Each mapper works independently on its chunk — this is embarrassingly parallel. The reducers then aggregate results from all mappers."

---

## Daemon Processes

### Hadoop 2.x has 5 main daemon processes:

| Daemon | Role | Layer |
|--------|------|-------|
| **NameNode** | Master of HDFS — stores metadata, manages namespace | HDFS |
| **DataNode** | Slave of HDFS — stores actual data blocks | HDFS |
| **ResourceManager** | Master of YARN — allocates resources across applications | YARN/MapReduce |
| **NodeManager** | Slave of YARN — manages containers on each node | YARN/MapReduce |
| **Secondary NameNode** | Checkpointing — merges edit logs with fsimage | HDFS |

### Hadoop 1.x vs 2.x Comparison (Important for Viva!):

| Hadoop 1.x | Hadoop 2.x | Change |
|------------|------------|--------|
| JobTracker | **ResourceManager** | Resource management separated |
| TaskTracker | **NodeManager** | Task management per node |
| No YARN | **YARN** (Yet Another Resource Negotiator) | Added resource management layer |
| Only MapReduce | Multiple frameworks (Spark, Tez, etc.) | YARN allows other processing models |

### How Daemons Work Together in Your Job:

```
1. You submit the MapReduce job
       ↓
2. ResourceManager receives the job request
       ↓
3. ResourceManager asks NodeManagers for available containers
       ↓
4. ApplicationMaster is launched (manages THIS specific job)
       ↓
5. ApplicationMaster negotiates containers for Map tasks
       ↓
6. NodeManagers launch Map tasks (your mapper.py runs here)
       ↓
7. Map output is shuffled and sorted
       ↓
8. ApplicationMaster negotiates containers for Reduce tasks
       ↓
9. NodeManagers launch Reduce tasks (your reducer.py runs here)
       ↓
10. Output written to HDFS
```

---

## Your Code Explained

### mapper.py — Line by Line

```python
import sys                                    # For reading from stdin

positive = ['good','great','happy','love','awesome']   # Positive keywords
negative = ['bad','hate','sad','worst','terrible']     # Negative keywords

first_line = True
for line in sys.stdin:                        # Hadoop streams input via stdin
    if first_line:
        first_line = False
        continue                              # Skip CSV header row "text"
    words = line.lower().split()              # Lowercase + tokenize
    pos = sum(1 for w in words if w in positive)  # Count positive words
    neg = sum(1 for w in words if w in negative)  # Count negative words
    if pos > neg:
        print("positive\t1")                  # Emit: key=positive, value=1
    elif neg > pos:
        print("negative\t1")                  # Emit: key=negative, value=1
    else:
        print("neutral\t1")                   # Emit: key=neutral, value=1
```

> **Key Point**: The mapper uses **Hadoop Streaming** — it reads from `stdin` and writes to `stdout`. Hadoop pipes the data through your script.

### reducer.py — Line by Line

```python
import sys

counts = {}                                   # Dictionary to hold counts

for line in sys.stdin:                        # Reads mapper output (sorted)
    line = line.strip()
    if '\t' not in line:
        continue                              # Skip malformed lines
    key, value = line.split("\t")             # Split "positive\t1" → key, value
    counts[key] = counts.get(key, 0) + int(value)  # Accumulate count

for key in counts:
    print("{}\t{}".format(key, counts[key]))  # Output final counts
```

### prepare.py — Line by Line

```python
import pandas as pd

df = pd.read_csv("training.1600000.processed.noemoticon.csv",
                  encoding="latin-1", header=None)
df.columns = ["sentiment","id","date","query","user","text"]

# Take 500 negative (start) + 500 positive (end) for balanced dataset
df = pd.concat([df.head(500), df.tail(500)])[["text"]]
df.to_csv("tweets.csv", index=False)
print("Done!")
```

---

## How to Demo "MapReduce Reduction" (10MB → 7MB) ⭐

> [!IMPORTANT]
> Your professor wants to see that MapReduce **reduces** the data size. Here's what this means and how to show it.

### What "Reduction" Means in MapReduce:

The **mapper** takes raw input (many tweets, lots of text) and produces **intermediate key-value pairs** (just classification + count). The **reducer** then **aggregates** these into a tiny summary.

### Size Comparison for Your Project:

| Stage | Data | Approximate Size |
|-------|------|-------------------|
| **Input** | 1000 tweets (full text) | ~77 KB (`tweets.csv`) |
| **Mapper Output** | 1000 lines of `positive\t1`, `negative\t1`, `neutral\t1` | ~12 KB |
| **Reducer Output** | 3 lines: `positive\t400`, `negative\t320`, `neutral\t280` | ~50 bytes |

**Reduction ratio: 77,825 bytes → ~50 bytes = 99.9% reduction!**

### Commands to Demo This:

```bash
# 1. Show input file size
hdfs dfs -ls /input/tweets.csv
# Or locally:
ls -lh tweets.csv          # Shows ~77KB

# 2. Run the MapReduce job
hadoop jar /path/to/hadoop-streaming.jar \
  -input /input/tweets.csv \
  -output /output/sentiment \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" \
  -file mapper.py \
  -file reducer.py

# 3. Show output file size
hdfs dfs -ls /output/sentiment/
# The part-00000 file will be tiny (~50 bytes)

# 4. Show the actual output
hdfs dfs -cat /output/sentiment/part-00000
# Output:
# negative    320
# neutral     280  
# positive    400

# 5. Compare sizes explicitly
echo "=== INPUT SIZE ==="
hdfs dfs -du -h /input/tweets.csv
echo "=== OUTPUT SIZE ==="
hdfs dfs -du -h /output/sentiment/part-00000
```

### What to Say to Professor:
> "The input file `tweets.csv` is approximately 77 KB containing 1000 full tweet texts. After the MapReduce job, the output is only about 50 bytes — just 3 lines showing the sentiment counts. This demonstrates how MapReduce **reduces** large volumes of data into meaningful aggregated results. The mapper extracts only the relevant information (sentiment classification), and the reducer condenses 1000 key-value pairs into just 3 final counts."

### For a More Dramatic Demo (Recommended):

Use the **full dataset** (238 MB) instead of the small 1000-tweet sample:

```bash
# Upload the FULL dataset
hdfs dfs -put training.1600000.processed.noemoticon.csv /input/

# Run MapReduce on it
hadoop jar /path/to/hadoop-streaming.jar \
  -input /input/training.1600000.processed.noemoticon.csv \
  -output /output/sentiment_full \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" \
  -file mapper.py \
  -file reducer.py

# Compare: 238 MB input → ~50 bytes output!
hdfs dfs -du -h /input/training.1600000.processed.noemoticon.csv   # 238 MB
hdfs dfs -du -h /output/sentiment_full/part-00000                   # ~50 bytes
```

**238 MB → 50 bytes = mind-blowing reduction!**

---

## Step-by-Step Demo Commands

### Pre-requisites Check:
```bash
# Verify Hadoop is installed and version >= 2.0
hadoop version

# Verify all daemons are running
jps
# Should show: NameNode, DataNode, ResourceManager, NodeManager, SecondaryNameNode

# If not running, start them:
start-dfs.sh
start-yarn.sh
```

### Full Demo Flow:

```bash
# Step 1: Create input directory in HDFS
hdfs dfs -mkdir -p /input

# Step 2: Upload tweets.csv to HDFS
hdfs dfs -put tweets.csv /input/

# Step 3: Verify upload
hdfs dfs -ls /input/
hdfs dfs -cat /input/tweets.csv | head -5

# Step 4: Show input file size (BEFORE)
hdfs dfs -du -h /input/tweets.csv

# Step 5: Find the Hadoop Streaming JAR path
find $HADOOP_HOME -name "hadoop-streaming*.jar"

# Step 6: Run the MapReduce job
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
  -input /input/tweets.csv \
  -output /output/sentiment \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" \
  -file mapper.py \
  -file reducer.py

# Step 7: Check job status (should say SUCCEEDED)
# You'll see progress: map 0% reduce 0% → map 100% reduce 100%

# Step 8: View results
hdfs dfs -cat /output/sentiment/part-00000

# Step 9: Show output file size (AFTER) — this is the "reduction" demo!
hdfs dfs -du -h /output/sentiment/

# Step 10: Clean up for re-runs (if needed)
hdfs dfs -rm -r /output/sentiment
```

### Testing Locally (Without Hadoop) — For Quick Verification:

```bash
# Test your mapper and reducer work correctly:
cat tweets.csv | python3 mapper.py | sort | python3 reducer.py
```

---

## Viva Questions & Answers

### Q1: What is HDFS and why do we need it?
> **A:** HDFS is Hadoop Distributed File System. We need it because traditional file systems can't handle petabytes of data across multiple machines. HDFS distributes data across a cluster, provides fault tolerance through replication, and enables data locality — processing data where it's stored rather than moving it.

### Q2: What is the default block size and replication factor?
> **A:** Block size is **128 MB** (in Hadoop 2.x; was 64 MB in 1.x). Replication factor is **3** by default. Both are configurable in `hdfs-site.xml`.

### Q3: What happens if a DataNode fails?
> **A:** The DataNode stops sending heartbeats to the NameNode. After a timeout (default 10 minutes + 30 seconds), the NameNode marks it as dead and replicates the lost blocks to other available DataNodes to maintain the replication factor.

### Q4: What is the difference between Hadoop 1.x and 2.x?
> **A:** The main difference is **YARN** (Yet Another Resource Negotiator). In 1.x, the JobTracker handled both resource management and job scheduling, creating a bottleneck. In 2.x, YARN separates these: ResourceManager handles resources, and ApplicationMaster handles individual jobs. This also allows non-MapReduce frameworks like Spark to run on Hadoop.

### Q5: What are the daemon processes and their roles?
> **A:** Five daemons:
> - **NameNode**: Master for HDFS, stores metadata
> - **DataNode**: Stores actual data blocks
> - **ResourceManager**: Master for YARN, manages cluster resources
> - **NodeManager**: Runs on each node, manages containers
> - **Secondary NameNode**: Performs checkpointing (merges edit logs with fsimage)

### Q6: Is Secondary NameNode a backup for NameNode?
> **A:** **No!** This is a common misconception. The Secondary NameNode performs **checkpointing** — it periodically downloads the edit log and fsimage from the NameNode, merges them, and sends the merged image back. This prevents the edit log from growing too large. For actual NameNode backup, Hadoop 2.x provides **NameNode HA (High Availability)** with a Standby NameNode.

### Q7: What is Hadoop Streaming?
> **A:** Hadoop Streaming is a utility that allows MapReduce jobs to be written in **any language** (Python, Ruby, etc.) instead of just Java. It uses **stdin/stdout** to communicate — Hadoop sends data to the mapper via stdin, mapper outputs to stdout, and similarly for the reducer.

### Q8: How does your mapper work?
> **A:** My mapper reads each tweet from stdin, tokenizes it into words, and counts positive and negative keyword matches. If more positive keywords are found, it emits `positive\t1`; if more negative, `negative\t1`; otherwise `neutral\t1`. Each tweet produces exactly one key-value pair.

### Q9: What happens between Map and Reduce (Shuffle & Sort)?
> **A:** After mapping, Hadoop performs:
> 1. **Partitioning**: Decides which reducer gets which keys (default: hash of key % number of reducers)
> 2. **Sorting**: Keys are sorted alphabetically
> 3. **Shuffling**: Data is transferred from mappers to reducers over the network
> 4. **Grouping**: All values for the same key are grouped together
> 
> So the reducer receives: `negative [1,1,1,...,1]`, then `neutral [1,1,1,...,1]`, then `positive [1,1,1,...,1]`

### Q10: Why did you use `sys.stdin` instead of opening a file?
> **A:** Because Hadoop Streaming works through Unix pipes. Hadoop reads the input file from HDFS, splits it, and pipes each split to a mapper instance via stdin. This is the standard approach for Hadoop Streaming — it makes the mapper/reducer work like Unix command-line tools.

### Q11: What is data locality in MapReduce?
> **A:** Data locality means Hadoop tries to run the Map task on the **same node** where the data block is stored. This minimizes network transfer. There are 3 levels: **data-local** (same node), **rack-local** (same rack), and **off-rack** (different rack). Data-local is fastest.

### Q12: How does MapReduce achieve fault tolerance?
> **A:** Multiple ways:
> - If a map/reduce task fails, the ApplicationMaster **re-runs** it on another node
> - If a node fails, all its tasks are re-scheduled on other nodes
> - HDFS replication ensures input data is always available
> - Speculative execution: if a task is slow, a duplicate is launched on another node

### Q13: Can you run this without Hadoop? How?
> **A:** Yes! Since we use Hadoop Streaming (stdin/stdout), we can test locally:
> ```bash
> cat tweets.csv | python3 mapper.py | sort | python3 reducer.py
> ```
> The `sort` command simulates Hadoop's shuffle & sort phase.

### Q14: What is the purpose of the Combiner?
> **A:** A Combiner is a "mini-reducer" that runs on the mapper's output **before** shuffle. It reduces network traffic by pre-aggregating locally. For example, if a mapper outputs 100x `positive\t1`, a combiner could reduce it to `positive\t100` before sending to the reducer. In our case, the reducer logic can also serve as a combiner since our operation (sum) is **associative and commutative**.

### Q15: What is your input data and why did you choose it?
> **A:** The input is the **Sentiment140 dataset** containing 1.6 million tweets labeled with sentiment. I used `prepare.py` to extract a balanced sample of 1000 tweets (500 negative + 500 positive) for demonstration. The full dataset is 238 MB, which is large enough to show MapReduce's value.

---

## Project Issues to Fix

### 1. Remove stale comment from mapper.py
Your `mapper.py` currently has debug comments at the bottom (lines 22-26) about running in local mode. Remove these before presenting.

### 2. Consider using the Hadoop streaming JAR correctly
Make sure you know the exact path to your `hadoop-streaming-*.jar`. Run:
```bash
find $HADOOP_HOME -name "hadoop-streaming*.jar"
```

### 3. Verify your job runs in YARN mode, not local mode
Your comment mentioned `job_local...` which means it ran in **local mode**. For the demo, ensure `mapred-site.xml` has:
```xml
<property>
    <name>mapreduce.framework.name</name>
    <value>yarn</value>
</property>
```

> [!WARNING]
> If the job runs in local mode (you see `job_local...` in logs), your professor will know it's not using the full Hadoop stack. Make sure YARN is configured and running!

---

## Presentation Flow (Recommended Order)

1. **Open with theory** (2 min): Explain HDFS architecture briefly with the diagram
2. **Explain MapReduce** (2 min): The 4 phases with your project as example
3. **Show daemon processes** (1 min): Run `jps` to show all 5 daemons running
4. **Walk through your code** (3 min): Explain mapper.py, reducer.py, prepare.py
5. **Run the demo** (3 min):
   - Show input file size
   - Run the MapReduce job
   - Show output
   - **Compare input vs output size** ← This is what professor wants!
6. **Answer questions** — Use the Q&A section above to prepare

Good luck! 🚀
