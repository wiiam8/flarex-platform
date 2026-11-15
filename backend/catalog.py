import json
from functools import lru_cache
from . import tables
from .config import DATA


@lru_cache(maxsize=1)
def context():
    return json.loads((DATA / "context.json").read_text(encoding="utf-8"))


def _range(s):
    s = s.dropna()
    return [float(s.min()), float(s.max())] if len(s) else None


@lru_cache(maxsize=1)
def records():
    cat = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    df, man = tables.tests(), {m["file"]: m for m in tables.manifest()}
    for r in cat:
        sub = df[df["inv"] == r["id"]]
        r["table_rows"] = sum(man[f]["rows"] for f in r["tables"] if f in man)
        r["stats"] = {"tests": int(len(sub)), "with_o2": int(sub["o2"].notna().sum()), "with_pressure": int(sub["p_atm"].notna().sum()),
                      "o2_range": _range(sub["o2"]), "p_psi_range": _range(sub["p_psi"]),
                      "fuels": sorted({str(x) for x in sub["fuel"].dropna()})[:8]}
        r["sha256"] = [man[f]["sha256"][:12] for f in r["tables"] if f in man]
        r["retrieved"] = man[r["tables"][0]]["retrieved"] if r["tables"] and r["tables"][0] in man else None
    return cat


def get(inv_id):
    return next((r for r in records() if r["id"] == inv_id), None)
