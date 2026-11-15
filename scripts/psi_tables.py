"""Download ONLY the PSI 'experimental tables' for the combustion investigations (about 0.2 MB in total),
never the multi-GB video/ZIP archives. Uses PSI's public web service (endpoints as documented by other
participants on 2026-11-08; not an official NASA API guarantee, so verify the output).
  python psi_tables.py                 # all 20 combustion records
  python psi_tables.py --ids 69 25     # just FLEX and BASS-II
Writes ./psi_tables/*.csv and ./psi_tables.zip  -> upload the zip."""
import argparse, json, os, sys, urllib.parse, urllib.request, zipfile
BASE = os.environ.get("PSI_BASE", "https://psi.nasa.gov/geode-py/ws")
MAX_BYTES = 5_000_000
KNOWN = {  # file names as listed publicly; used only if the detail record can't be parsed
 10: ["PSI-10_Experimental table_Flame Design_Normal Flame.csv", "PSI-10_Experimental table_Flame Design_Inverse Flame.csv"],
 20: ["PSI-20_Experimental table_ACME BRE.csv"], 21: ["PSI-21_Experimental table_CLD Flame.csv"],
 22: ["PSI-22_Experimental table_ACME E-FIELD Flames.csv"], 23: ["PSI-23_Experimental table_ACME s-Flame.csv"],
 25: ["PSI-25_Experimental table_BASS-II.csv"], 26: ["PSI-26_Experimental table_BASS.csv"],
 39: ["PSI-39_Experimental table_CFI.csv"], 47: ["PSI-47_Experimental table_DAFT.csv"],
 68: ["PSI-68_Experimental table_Flex2.csv"], 69: ["PSI-69_Experimental table_FLEX.csv"],
 98: ["PSI-98_Experimental table_SAFFIRE-1.csv"], 99: ["PSI-99_Experimental table_SAFFIRE-2.csv"],
 100: ["PSI-100_Experimental table_SAFFIRE-3.csv"], 101: ["PSI-101_Experimental table_SAME-R.csv"],
 102: ["PSI-102_Experimental table_SAME.csv"], 106: ["PSI-106_Experimental table_Slice.csv"],
 107: ["PSI-107_Experimental table_Spice.csv"], 142: ["PSI-142_Experimental table_Data Summary Table.csv"],
 159: ["PSI-159_Experimental table_CFI-G_Normal Flames.csv", "PSI-159_Experimental table_CFI-G_Inverse Flames.csv"]}
EXT = (".csv", ".xlsx", ".xls", ".txt")


def get(url, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": "flarex-helper"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read(limit + 1 if limit else -1)
    if limit and len(data) > limit:
        raise RuntimeError(f"larger than {limit} bytes, refusing")
    return data


def _strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from _strings(v)
    elif isinstance(x, list):
        for v in x: yield from _strings(v)


def table_names(pid):
    """File names from the record's experimentalTable list; falls back to the known names."""
    try:
        d = json.loads(get(f"{BASE}/repo/investigations/PSI-{pid}"))
        d = d.get("_source", d) if isinstance(d, dict) else {}
        names = []
        for s in _strings(d.get("experimentalTable", [])):
            base = os.path.basename(s)
            if base.lower().endswith(EXT) and base not in names:
                names.append(base)
        if names:
            return names, "detail record"
    except Exception as e:
        print(f"  (detail lookup failed: {e})")
    return KNOWN.get(pid, []), "built-in name list"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ids", nargs="*", type=int); ap.add_argument("--out", default="psi_tables")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    ok, total = [], 0
    for pid in a.ids or sorted(KNOWN):
        names, how = table_names(pid)
        print(f"PSI-{pid}: {len(names)} table(s) via {how}")
        for n in names:
            try:
                data = get(f"{BASE}/studies/PSI-{pid}/download?file={urllib.parse.quote(n)}", MAX_BYTES)
                open(os.path.join(a.out, n), "wb").write(data); ok.append(n); total += len(data)
                print(f"  OK   {n}  ({len(data)/1000:.1f} KB)")
            except Exception as e:
                print(f"  FAIL {n}: {e}")
    if ok:
        with zipfile.ZipFile("psi_tables.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for n in ok: z.write(os.path.join(a.out, n), n)
        print(f"\nDone: {len(ok)} files, {total/1000:.0f} KB. Upload psi_tables.zip")
    else:
        print("\nNothing downloaded. Open each record page on psi.nasa.gov, find 'Experimental table', and download that one small file manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
