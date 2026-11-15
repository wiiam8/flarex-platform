"""Parse NASA PSI experimental tables into one test-level table. Source values are preserved (raw columns),
conversions are explicit, nothing is guessed: unparseable cells become None and are flagged."""
import csv, hashlib, io, re
from functools import lru_cache
import pandas as pd
from .config import TABLES, BAR_PER_ATM, MMHG_PER_ATM, RETRIEVED

NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def read_table(path):
    raw = path.read_bytes()
    try:
        text, enc = raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("cp1252"), "cp1252"
    rows = list(csv.DictReader(io.StringIO(text)))
    rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in rows]
    return rows, enc, raw


def num(x):
    """Strict number: '0.21' yes; '', '-', 'RAMPED', '~ 21.5' no."""
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def first_number(x):
    m = NUM.search(str(x))
    return float(m.group()) if m else None


def nonempty(r):
    return any(v for v in r.values())


@lru_cache(maxsize=1)
def manifest():
    out = []
    for p in sorted(TABLES.glob("*.csv")):
        rows, enc, raw = read_table(p)
        psi = p.name.split("_")[0]
        out.append({"file": p.name, "psi": psi, "rows": sum(nonempty(r) for r in rows), "physical_rows": len(rows),
                    "columns": len(rows[0]) if rows else 0, "bytes": len(raw), "encoding": enc,
                    "sha256": hashlib.sha256(raw).hexdigest(), "retrieved": RETRIEVED})
    return out


def _t(inv, psi, file, i, **kw):
    d = {"inv": inv, "psi": psi, "file": file, "row": i, "test_id": None, "fuel": None, "fuel_class": None, "o2": None, "p_atm": None,
         "p_raw": None, "o2_raw": None, "flame": None, "diluent": None, "d0_mm": None, "ext_mm": None, "burn_s": None, "end": None, "flags": []}
    d.update(kw)
    return d


def _flex(rows, f):
    ks = list(rows[0].keys())
    pc, oc, nc, cc, hc = ks[5], ks[6], ks[7], ks[8], ks[9]
    out = []
    for i, r in enumerate(rows, 1):
        if not nonempty(r): continue
        fl, p = [], num(r[pc])
        if p is not None and p <= 0:
            fl.append("pressure_zero_excluded"); p_atm = None
        else:
            p_atm = None if p is None else p / MMHG_PER_ATM
        dil = "O2/N2" + ("/CO2" if (num(r[cc]) or 0) > 0 else "") + ("/He" if (num(r[hc]) or 0) > 0 else "")
        out.append(_t("FLEX", "PSI-69", f, i, test_id=r[ks[1]], fuel=r["Fuel"], fuel_class="liquid", o2=num(r[oc]), o2_raw=r[oc], p_atm=p_atm,
                      p_raw=f"{r[pc]} mmHg", diluent=dil, d0_mm=num(r[ks[10]]), ext_mm=num(r[ks[11]]), burn_s=num(r[ks[13]]), end=r["Test end"], flags=fl))
    return out


def _flame_design(rows, f, kind):
    out = []
    for i, r in enumerate(rows, 1):
        if not nonempty(r): continue
        fl = []
        if kind == "Normal":
            o2, fuel = num(r["XO2 (init)"]), r["Fuel"]
            if any("RAMP" in v.upper() for v in r.values()): fl.append("ramped_flow_qualifier")
        else:
            o2, fuel = num(r["XO2"]), "ethylene (XC2H4 column)"
        p = num(r["pmean (atm)"])
        out.append(_t("FLAMEDESIGN", "PSI-10", f, i, test_id=r["Test"], fuel=fuel, fuel_class="gas", o2=o2, o2_raw=str(o2), p_atm=p,
                      p_raw=f"{r['pmean (atm)']} atm", flame=kind, flags=fl))
    return out


def _cfig(rows, f, kind):
    o2c = " XO2 before test".strip() if kind == "Normal" else "XO2"
    out = []
    for i, r in enumerate(rows, 1):
        if not r.get("Test"): continue          # PSI-159 inverse has trailing blank rows
        p_bar = num(r["approx p (bar)"])
        end = r.get("Self-ext or flow term") or r.get("Self -ext or flow term") or ""
        out.append(_t("CFIG", "PSI-159", f, i, test_id=r["Test"], fuel=r["Fuel"], fuel_class="gas", o2=num(r[o2c]), o2_raw=r[o2c],
                      p_atm=None if p_bar is None else p_bar / BAR_PER_ATM, p_raw=f"{r['approx p (bar)']} bar", flame=kind,
                      burn_s=num(r["burn time (sec)"]), end=end if end not in ("", "-") else None,
                      flags=[] if r.get("Hot ignition") else ["ignition_not_reported"]))
    return out


def _cfi(rows, f):
    out = []
    for i, r in enumerate(rows, 1):
        if not nonempty(r): continue
        pm = NUM.search(r["Pressure"])
        out.append(_t("CFI", "PSI-39", f, i, test_id=r["Flex Number"], fuel=r["Fuel"], fuel_class="liquid", o2=num(r["Oxygen"]), o2_raw=r["Oxygen"],
                      p_atm=float(pm.group()) if pm and "atm" in r["Pressure"] else None, p_raw=r["Pressure"]))
    return out


def _bass2(rows, f):
    k = next(c for c in rows[0] if "initial" in c.lower() and "O2" in c)
    out = []
    for i, r in enumerate(rows, 1):
        if not nonempty(r): continue
        v = num(r[k])
        out.append(_t("BASSII", "PSI-25", f, i, test_id=r["Test #"], fuel=r["Fuel Sample Material"], fuel_class="solid",
                      o2=None if v is None else v / 100, o2_raw=r[k], flags=["no_pressure_column"]))
    return out


def _saffire(rows, f, inv, psi, col):
    out = []
    for i, r in enumerate(rows, 1):
        if not r.get("Sample Number") and not r.get(col) : continue
        raw = r.get(col, "")
        v = first_number(raw)
        fl = ["no_pressure_column"] + (["o2_approximate"] if raw and num(raw) is None else [])
        if v is not None:
            out.append(_t(inv, psi, f, i, test_id=r.get("Sample Number"), fuel=r.get("Material"), fuel_class="solid", o2=v / 100, o2_raw=raw, flags=fl))
    return out


@lru_cache(maxsize=1)
def tests():
    parts = []
    for p in sorted(TABLES.glob("*.csv")):
        rows, _, _ = read_table(p)
        n = p.name
        if not rows: continue
        if n.startswith("PSI-69_"): parts += _flex(rows, n)
        elif n.startswith("PSI-10_"): parts += _flame_design(rows, n, "Inverse" if "Inverse" in n else "Normal")
        elif n.startswith("PSI-159_"): parts += _cfig(rows, n, "Inverse" if "Inverse" in n else "Normal")
        elif n.startswith("PSI-39_"): parts += _cfi(rows, n)
        elif n.startswith("PSI-25_"): parts += _bass2(rows, n)
        elif n.startswith("PSI-98_"): parts += _saffire(rows, n, "SAFFIRE1", "PSI-98", "Percent O2")
        elif n.startswith("PSI-99_"): parts += _saffire(rows, n, "SAFFIRE2", "PSI-99", "Percent O2 (Note 1)")
    df = pd.DataFrame(parts)
    df["psi_row"] = df["file"].str.slice(0, 7).str.strip("_") + " row " + df["row"].astype(str)
    dup = df.duplicated(["inv", "test_id"], keep=False) & df["test_id"].notna()
    for i in df.index[dup]:
        df.at[i, "flags"] = df.at[i, "flags"] + ["duplicate_test_id"]
    df["p_psi"] = df["p_atm"] * 14.696
    return df


@lru_cache(maxsize=1)
def planned_flex2():
    rows, _, _ = read_table(TABLES / "PSI-68_Experimental table_Flex2.csv")
    o2 = sorted({float(x) for r in rows for x in NUM.findall(r["Oxygen Mole Fraction"])})
    pr = sorted({float(x) for r in rows for x in NUM.findall(r["Ambient Pressure (atm)"])})
    return {"o2_fractions": o2, "pressures_atm": pr}
