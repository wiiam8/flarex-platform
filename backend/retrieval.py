"""Keyword retrieval (BM25) over source passages. Swap in embeddings later behind the same search() signature."""
import math, re
from collections import Counter
_STOP = set("the a an of and or to in is are was for on with by as at from that this it be can".split())


def tok(t):
    return [w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in _STOP]


def search(query, passages, k=5, k1=1.5, b=.75):
    docs = [tok(p["text"] + " " + p.get("inv", "")) for p in passages]
    q = tok(query)
    if not q or not docs:
        return []
    avg = sum(map(len, docs)) / len(docs) or 1
    df = Counter(w for d in docs for w in set(d))
    res = []
    for p, d in zip(passages, docs):
        tf, s = Counter(d), 0.0
        for w in q:
            if tf[w]:
                idf = math.log(1 + (len(docs) - df[w] + .5) / (df[w] + .5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
        if s > 0:
            res.append((s, p))
    return [p for s, p in sorted(res, key=lambda x: -x[0])[:k]]
