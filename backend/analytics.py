"""Charts and computed facts from the real test table. Every number here is computed from the PSI files at load time."""
import numpy as np
from . import tables, catalog
from .config import MOON_O2, MOON_P_PSI, PSI_PER_ATM

O2_BIN, P_BIN, P_MAX = 5, 2, 48          # percentage points, psi, psi
MIN_GROUP = 5                            # a comparable group needs at least this many points to be charted


def zone_stats():
    df = tables.tests()
    both = df[df["o2"].notna() & df["p_atm"].notna()]
    inz = both[(both["o2"] >= MOON_O2) & (both["p_psi"] <= MOON_P_PSI)]
    hi = df[df["o2"] >= MOON_O2]
    by = {}
    for inv, sub in df.groupby("inv"):
        h = sub[sub["o2"] >= MOON_O2]
        by[inv] = {"tests": int(len(sub)), "o2_ge_30": int(len(h)), "with_pressure_ge_30": int(h["p_atm"].notna().sum()),
                   "in_zone": int(((sub["o2"] >= MOON_O2) & (sub["p_psi"] <= MOON_P_PSI)).sum()),
                   "closest_psi_at_o2_ge_30": None if h["p_psi"].dropna().empty else round(float(h["p_psi"].min()), 2)}
    solid = df[df["fuel_class"] == "solid"]
    return {"zone": {"o2_pct": MOON_O2 * 100, "pressure_psi": MOON_P_PSI}, "tests_total": int(len(df)),
            "tests_with_o2_and_pressure": int(len(both)), "tests_in_zone": int(len(inz)), "tests_o2_ge_30": int(len(hi)),
            "by_investigation": by, "solid": {"tests": int(len(solid)), "with_pressure": int(solid["p_atm"].notna().sum()),
                                              "max_o2_pct": round(float(solid["o2"].max()) * 100, 1) if len(solid) else None}}


def heatmap(inv=None):
    df = tables.tests()
    if inv and inv != "all":
        df = df[df["inv"] == inv]
    both = df[df["o2"].notna() & df["p_psi"].notna()]
    ox, py = np.arange(0, 100 + O2_BIN, O2_BIN), np.arange(0, P_MAX + P_BIN, P_BIN)
    H, _, _ = np.histogram2d(both["p_psi"].clip(upper=P_MAX - 1e-9), (both["o2"] * 100).clip(upper=100 - 1e-9), bins=[py, ox])
    only = df[df["o2"].notna() & df["p_psi"].isna()]
    S, _ = np.histogram((only["o2"] * 100).clip(upper=100 - 1e-9), bins=ox)
    return {"o2_edges": ox.tolist(), "p_edges": py.tolist(), "counts": H.astype(int).tolist(), "o2_only": S.astype(int).tolist(),
            "o2_only_n": int(len(only)), "plotted": int(len(both)), "zone": zone_stats()["zone"],
            "in_zone": int(((both["o2"] >= MOON_O2) & (both["p_psi"] <= MOON_P_PSI)).sum()),
            "investigations": sorted(tables.tests()["inv"].unique().tolist())}


DATASETS = {"flex": {"inv": "FLEX", "x": "o2", "y": "ext_mm", "ylabel": "Visible flame extinction diameter (mm)", "title": "FLEX: oxygen vs extinction diameter",
                     "keys": ["fuel", "diluent"], "filter": lambda d: d[(d["end"] == "Extinction") & d["ext_mm"].notna()],
                     "note": "Only tests that ended in extinction with a reported diameter. Point size = initial droplet diameter, because it also affects extinction size."},
            "cfig": {"inv": "CFIG", "x": "o2", "y": "burn_s", "ylabel": "Burn time (s)", "title": "CFI-G: oxygen vs burn time",
                     "keys": ["flame", "fuel"], "filter": lambda d: d[d["burn_s"].notna()],
                     "note": "Only tests with a reported burn time. Colour shows how the flame ended (SE self-extinguished, FT flow termination)."}}


def _prep(name):
    cfg = DATASETS[name]
    d = tables.tests()
    d = cfg["filter"](d[d["inv"] == cfg["inv"]])
    d = d[d["o2"].notna() & d["p_atm"].notna()].copy()
    d["pband"] = (d["p_atm"] * 10).round() / 10
    return cfg, d


def comparable_groups(name):
    cfg, d = _prep(name)
    g = d.groupby(cfg["keys"] + ["pband"]).size().reset_index(name="n")
    out = []
    for r in g.to_dict("records"):
        parts = [str(r[k]) for k in cfg["keys"]]
        out.append({"key": "|".join(parts + [f"{r['pband']:.1f}"]), "label": " / ".join(parts) + f" @ {r['pband']:.1f} atm",
                    "n": int(r["n"]), "chartable": int(r["n"]) >= MIN_GROUP})
    return sorted(out, key=lambda x: -x["n"])


def comparable_series(name, key):
    cfg, d = _prep(name)
    parts = key.split("|")
    if len(parts) != len(cfg["keys"]) + 1:
        raise ValueError("bad group key")
    m = d["pband"].round(1) == round(float(parts[-1]), 1)
    for k, v in zip(cfg["keys"], parts[:-1]):
        m &= d[k].astype(str) == v
    g = d[m]
    if len(g) < MIN_GROUP:
        raise ValueError(f"Only {len(g)} comparable tests; at least {MIN_GROUP} are needed to chart them together.")
    clean = lambda v: None if v is None or v != v else v      # NaN is not valid JSON
    pts = [{"x": float(r.o2) * 100, "y": float(getattr(r, cfg["y"])), "id": clean(r.test_id), "end": clean(r.end), "d0": clean(r.d0_mm),
            "src": r.psi_row} for r in g.itertuples()]
    return {"title": cfg["title"], "ylabel": cfg["ylabel"], "xlabel": "Initial oxygen (% of atmosphere, mole fraction x 100)", "note": cfg["note"],
            "group": " / ".join(parts[:-1]) + f" @ {parts[-1]} atm (+-0.05)", "n": len(pts), "points": pts}


def quality_flags():
    df = tables.tests()
    out = {}
    for inv, sub in df.groupby("inv"):
        c = {}
        for fl in sub["flags"]:
            for f in fl:
                c[f] = c.get(f, 0) + 1
        if c: out[inv] = c
    return out


def facts():
    """Computed, citable facts for the copilot (ids start with D-)."""
    z, out = zone_stats(), []
    for r in catalog.records():
        s = r["stats"]
        if not s["tests"]: continue
        o2 = f"oxygen {s['o2_range'][0]*100:.0f}% to {s['o2_range'][1]*100:.0f}%" if s["o2_range"] else "no oxygen values"
        pr = f"pressure {s['p_psi_range'][0]:.1f} to {s['p_psi_range'][1]:.1f} psi" if s["p_psi_range"] else "no pressure values"
        out.append({"id": f"D-{r['id']}-1", "inv": r["id"], "source": f"{r['psi']} experimental table",
                    "text": f"{r['name']} ({r['psi']}): the public table lists {s['tests']} tests with {o2} ({s['with_o2']} tests with a value) and {pr} ({s['with_pressure']} tests with a value)."})
    zz = z["by_investigation"]
    out.append({"id": "D-ZONE-1", "inv": "", "source": "Computed from all loaded PSI tables",
                "text": f"Moon-base reference zone (30% O2 or more at 10.2 psi or less): {z['tests_in_zone']} of {z['tests_with_o2_and_pressure']} tests with both oxygen and pressure fall inside it: CFI-G {zz['CFIG']['in_zone']}, Flame Design {zz['FLAMEDESIGN']['in_zone']}, FLEX {zz['FLEX']['in_zone']}."})
    out.append({"id": "D-ZONE-2", "inv": "FLEX", "source": "PSI-69 experimental table",
                "text": f"FLEX has {zz['FLEX']['o2_ge_30']} tests at 30% O2 or more; the lowest pressure among them is {zz['FLEX']['closest_psi_at_o2_ge_30']} psi, just above the 10.2 psi reference."})
    out.append({"id": "D-SOLID-1", "inv": "BASS", "source": "PSI-25, PSI-98, PSI-99 experimental tables",
                "text": f"Solid-fuel tables (BASS-II, Saffire-I and II) list {z['solid']['tests']} tests with oxygen up to {z['solid']['max_o2_pct']}% and {z['solid']['with_pressure']} tests with a pressure value."})
    f2 = tables.planned_flex2()
    out.append({"id": "D-FLEX2-1", "inv": "FLEX2", "source": "PSI-68 experimental table",
                "text": f"FLEX-2's public table lists planned conditions, not measurements: oxygen mole fractions {f2['o2_fractions']} and pressures {f2['pressures_atm']} atm."})
    return out
