"""PDF evidence briefing (reportlab). ASCII-safe text so standard fonts render correctly everywhere."""
import io
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from . import analytics, catalog, relevance, tables
from .config import RETRIEVED, MOON_O2, MOON_P_PSI

SUB = {"\u2082": "2", "\u2265": ">=", "\u2264": "<=", "\u2013": "-", "\u2014": "-", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00b1": "+-", "\u00d7": "x"}


def safe(t):
    t = "" if t is None else str(t)
    for k, v in SUB.items(): t = t.replace(k, v)
    return t.encode("latin-1", "replace").decode("latin-1").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _heat(sc, w=170 * mm, h=70 * mm):
    d, hm = Drawing(w, h), analytics.heatmap()
    L, B, W, H = 28, 18, w - 36, h - 30
    ox, py, C = hm["o2_edges"], hm["p_edges"], hm["counts"]
    mx = max(max(r) for r in C) or 1
    cw, ch = W / (len(ox) - 1), H / (len(py) - 1)
    for i, row in enumerate(C):
        for j, v in enumerate(row):
            if v:
                a = .15 + .85 * v / mx
                d.add(Rect(L + j * cw, B + i * ch, cw, ch, fillColor=colors.Color(.1, .45, .9, alpha=a), strokeColor=None))
    zx = L + (MOON_O2 * 100 / 100) * W
    d.add(Rect(zx, B, L + W - zx, MOON_P_PSI / py[-1] * H, fillColor=None, strokeColor=colors.Color(.99, .24, .13), strokeWidth=1.6))
    d.add(Line(L, B, L + W, B)); d.add(Line(L, B, L, B + H))
    for o in (0, 25, 50, 75, 100): d.add(String(L + o / 100 * W - 6, B - 11, f"{o}%", fontSize=7))
    for p in (0, 10, 20, 30, 40): d.add(String(4, B + p / py[-1] * H - 2, f"{p}", fontSize=7))
    d.add(String(L, h - 8, "Tests by oxygen (x) and pressure in psi (y); red box = Moon-base reference zone", fontSize=7))
    if sc.get("oxygen_pct") is not None and sc.get("pressure_psi") is not None:
        d.add(String(L + sc["oxygen_pct"] / 100 * W - 3, B + min(sc["pressure_psi"], py[-1]) / py[-1] * H - 3, "X", fontSize=10, fillColor=colors.red))
    return d


def build(sc):
    ranked, gp, z = relevance.rank(sc), relevance.gaps(sc), analytics.zone_stats()
    st = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", parent=st["Title"], fontSize=20, alignment=0, spaceAfter=2)
    H2 = ParagraphStyle("h2", parent=st["Heading2"], fontSize=12, textColor=colors.HexColor("#0b3d91"), spaceBefore=10)
    B = ParagraphStyle("b", parent=st["BodyText"], fontSize=9, leading=12)
    S = ParagraphStyle("s", parent=B, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#444444"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="FLARE-X evidence briefing", author="FLARE-X")
    P = lambda t, s=B: Paragraph(safe(t), s)
    el = [P("FLARE-X Evidence Briefing", H1), P(f"Generated {date.today().isoformat()} from NASA PSI experimental tables retrieved {RETRIEVED}. "
          "Relevance ranking only: this is not a fire-risk prediction or safety rating.", S), Spacer(1, 6), P("Scenario", H2)]
    rows = [["Environment", sc.get("environment")], ["Concern", sc.get("concern")], ["Gravity", sc.get("gravity")], ["Fuel class", sc.get("fuel")],
            ["Oxygen", "unset" if sc.get("oxygen_pct") is None else f"{sc['oxygen_pct']:g}%"],
            ["Total pressure", "unset" if sc.get("pressure_psi") is None else f"{sc['pressure_psi']:g} psi"]]
    t = Table([[P(a), P(b)] for a, b in rows], colWidths=[40 * mm, 100 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .25, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f8"))]))
    el.append(t)
    if relevance.mismatch(sc): el += [Spacer(1, 4), P("WARNING: " + relevance.mismatch(sc), B)]
    el += [P("Key findings from the data", H2),
           P(f"- {z['tests_in_zone']} of {z['tests_with_o2_and_pressure']} tests with both oxygen and pressure fall inside the Moon-base reference zone "
             f"(30% O2 or more, 10.2 psi or less): CFI-G {z['by_investigation']['CFIG']['in_zone']}, Flame Design {z['by_investigation']['FLAMEDESIGN']['in_zone']}, FLEX {z['by_investigation']['FLEX']['in_zone']}."),
           P(f"- FLEX has {z['by_investigation']['FLEX']['o2_ge_30']} tests at 30% O2 or more; the lowest pressure among them is {z['by_investigation']['FLEX']['closest_psi_at_o2_ge_30']} psi."),
           P(f"- Solid-fuel tables list {z['solid']['tests']} tests, oxygen up to {z['solid']['max_o2_pct']}%, and {z['solid']['with_pressure']} with a pressure value."),
           P("Oxygen and pressure coverage", H2), _heat(sc), P("Ranked evidence", H2)]
    hdr = ["Investigation", "Evidence", "Band", "Score", "Cover", "Tests near O2/P"]
    data = [[P(h, S) for h in hdr]]
    for x in ranked[:10]:
        m = x["matches"]
        near = "n/a" if m["both"] is None else f"{m['both']} both (O2 {m['o2']}, P {m['pressure']})"
        data.append([P(f"{x['name']} ({x['psi']})", S), P(x["evidence"], S), P(x["band"], S), P(f"{x['score']:.0%}", S), P(f"{x['coverage']:.0%}", S), P(near, S)])
    t = Table(data, colWidths=[62 * mm, 16 * mm, 32 * mm, 12 * mm, 12 * mm, 40 * mm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f3")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el += [t, P("Score = weighted match on the dimensions that could be scored; coverage = share of total weight available. Missing data is excluded, never counted as a match. "
                "Order: evidence type (Direct, Indirect, Gap), then score.", S), P("Research gaps", H2)]
    el += [P("- " + g) for g in gp] or [P("- None detected for this scenario.")]
    el.append(P("Citations", H2))
    for x in ranked[:6]:
        r = catalog.get(x["id"])
        link = f"https://doi.org/{r['doi']}" if r.get("doi") else r["links"][0]["url"]
        el.append(P(f"[{r['psi']}] {r['name']}. {link}. Table file(s): {', '.join(r['tables'])} (SHA-256 {', '.join(r['sha256'])}...), retrieved {RETRIEVED}.", S))
    el += [Spacer(1, 6), P("Source: NASA Physical Sciences Informatics (PSI). NASA does not endorse FLARE-X. Values were parsed from public experimental tables; "
                           "verify against the PSI record before citing. Units converted: mmHg and bar to atm to psi.", S)]
    doc.build(el, onFirstPage=_foot, onLaterPages=_foot)
    return buf.getvalue()


def _foot(c, d):
    c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(colors.grey)
    c.drawString(18 * mm, 9 * mm, "FLARE-X evidence briefing - relevance only, not a safety rating"); c.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {d.page}"); c.restoreState()
