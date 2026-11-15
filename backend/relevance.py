"""Habitat Relevance Engine. Scores how well *documented test conditions* match a scenario. Not a fire-risk model.
Missing dimensions are excluded and reported as coverage, never counted as a match."""
from . import tables, catalog
from .config import O2_TOL, P_TOL, MOON_O2, MOON_P_PSI

WEIGHTS = {"oxygen": .25, "pressure": .20, "fuel": .20, "gravity": .15, "objective": .10, "measurement": .10}
EXPECTED_GRAVITY = {"spacecraft": "micro", "lunar": "lunar", "mars": "mars", "rover": None}
GNAME = {"micro": "microgravity", "lunar": "lunar gravity", "mars": "Martian gravity", "normal": "normal gravity"}
KEYWORDS = {"detection": ["smoke", "aerosol", "dust"], "suppression": ["extinction", "suppress"],
            "prevention": ["spread", "burn", "flame output"], "gas-phase": ["flame", "burn"]}
MIN_COVERAGE = 0.2


def mismatch(sc):
    exp = EXPECTED_GRAVITY.get(sc.get("environment"))
    g = sc.get("gravity", "micro")
    if exp and exp != g:
        return (f"Scenario mismatch: this environment normally has {GNAME[exp]}, but {GNAME[g]} was selected. "
                "Correct it or keep it as an explicit hypothetical design condition.")
    return ""


def near(df, sc):
    """Tests close to the scenario: O2 within +-3 points, pressure within +-10%."""
    o2, psi = sc.get("oxygen_pct"), sc.get("pressure_psi")
    mo = df["o2"].sub(o2 / 100).abs().le(O2_TOL + 1e-9) if o2 is not None else None
    mp = df["p_psi"].sub(psi).abs().le(P_TOL * psi) if psi is not None else None
    return mo, mp


def _tier(n):
    return 1.0 if n >= 3 else 0.5 if n >= 1 else 0.0


def score(rec, sc, weights=None):
    w = weights or WEIGHTS
    df = tables.tests()
    sub = df[df["inv"] == rec["id"]]
    mo, mp = near(sub, sc)
    n_o2 = int(mo.sum()) if mo is not None else None
    n_p = int(mp.sum()) if mp is not None else None
    both = int((mo & mp).sum()) if mo is not None and mp is not None else None
    concern, fuel = sc.get("concern", "suppression"), sc.get("fuel", "any")
    obj = 1.0 if concern in rec["direct"] else 0.4 if concern in rec["indirect"] else 0.0
    vals = {
        "oxygen": None if sc.get("oxygen_pct") is None or not sub["o2"].notna().any() else _tier(n_o2),
        "pressure": None if sc.get("pressure_psi") is None or not sub["p_atm"].notna().any() else _tier(n_p),
        "fuel": None if fuel == "any" or not rec.get("fuel_class") else float(rec["fuel_class"] == fuel),
        "gravity": 1.0 if sc.get("gravity", "micro") == "micro" else 0.3,
        "objective": obj,
        "measurement": _measurement(rec, sub, concern),
    }
    why = {"oxygen": "scenario oxygen unset, or no oxygen reported in this table", "pressure": "scenario pressure unset, or no pressure reported in this table",
           "fuel": "fuel not specified or not reported", "measurement": "no measured outcome column in this table"}
    dims = [{"name": k, "weight": w[k], "value": vals[k], "note": why.get(k, "")} for k in w]
    avail = sum(d["weight"] for d in dims if d["value"] is not None)
    cov = avail / sum(w.values())
    s = sum(d["weight"] * d["value"] for d in dims if d["value"] is not None) / avail if avail else 0.0
    band = "Insufficient information" if cov < MIN_COVERAGE else ("Strong" if s >= .7 else "Moderate" if s >= .4 else "Limited")
    if MIN_COVERAGE <= cov < .5: band += " (low coverage)"
    f = vals["fuel"]
    ev = "Direct" if obj == 1.0 and f != 0.0 else "Indirect" if (obj > 0 or f == 1.0) else "Gap"
    return {"id": rec["id"], "name": rec["name"], "psi": rec["psi"], "family": rec["family"], "score": s, "coverage": cov, "band": band, "evidence": ev,
            "dims": dims, "missing": [d["name"] for d in dims if d["value"] is None],
            "matches": {"o2": n_o2, "pressure": n_p, "both": both, "tests": int(len(sub)),
                        "in_zone": int(((sub["o2"] >= MOON_O2) & (sub["p_psi"] <= MOON_P_PSI)).sum())}}


def _measurement(rec, sub, concern):
    """Does the table contain a measured outcome relevant to the concern? Only where outcome columns exist."""
    if not len(sub): return None
    has = {"suppression": sub["ext_mm"].notna().any(),
           "prevention": sub["burn_s"].notna().any(), "gas-phase": sub["burn_s"].notna().any() or sub["end"].notna().any(),
           "detection": False}
    if sub["ext_mm"].notna().any() or sub["burn_s"].notna().any() or sub["end"].notna().any():
        return 1.0 if has.get(concern) else 0.0
    return None


ORDER = {"Direct": 0, "Indirect": 1, "Gap": 2}


def rank(sc, weights=None):
    """Order: evidence type first (Direct, Indirect, Gap), then score on available dimensions, then coverage."""
    out = [score(r, sc, weights) for r in catalog.records()]
    return sorted(out, key=lambda x: (x["band"].startswith("Insufficient"), ORDER[x["evidence"]], -x["score"], -x["coverage"]))


def gaps(sc):
    df, out = tables.tests(), []
    if sc.get("gravity", "micro") in ("lunar", "mars"):
        out.append("No partial-gravity combustion data is in PSI per the challenge text (verify). Microgravity and normal-gravity results can only bound it.")
    o2, psi, fuel = sc.get("oxygen_pct"), sc.get("pressure_psi"), sc.get("fuel", "any")
    pool = df if fuel == "any" else df[df["fuel_class"] == fuel]
    label = "" if fuel == "any" else f"{fuel}-fuel "
    if o2 is not None and psi is not None:
        mo, mp = near(pool, sc)
        n = int((mo & mp).sum())
        if n == 0:
            out.append(f"No {label}test in the loaded tables reports both oxygen within {O2_TOL*100:.0f} points of {o2:g}% and pressure within {P_TOL*100:.0f}% of {psi:g} psi.")
        else:
            by = pool[mo & mp].groupby("inv").size().to_dict()
            out.append(f"{n} {label}tests are near {o2:g}% O2 and {psi:g} psi: " + ", ".join(f"{k} ({v})" for k, v in by.items()) + ".")
    solid = df[df["fuel_class"] == "solid"]
    if (fuel in ("solid", "any")) and psi is not None and solid["p_atm"].notna().sum() == 0:
        out.append("Solid-fuel tables (BASS-II, Saffire) report oxygen but no pressure, so pressure cannot be matched for solid materials.")
    if fuel != "any" and not any(r["fuel_class"] == fuel and sc.get("concern") in r["direct"] for r in catalog.records()):
        out.append(f"No loaded {fuel}-fuel investigation directly addresses {sc.get('concern')}.")
    return out
