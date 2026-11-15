import io, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend import analytics as A, briefing, catalog, copilot, relevance as R, tables as T
from backend.api import app

client = TestClient(app)
MOON = {"environment": "lunar", "concern": "suppression", "gravity": "lunar", "fuel": "any", "oxygen_pct": 30, "pressure_psi": 10.2}


# ---------- data integrity (real PSI files) ----------
def test_manifest_matches_published_files():
    m = T.manifest()
    assert len(m) == 22 and sum(x["rows"] for x in m) == 2009 and sum(x["bytes"] for x in m) == 211116
    assert all(len(x["sha256"]) == 64 for x in m)


def test_flex_parsing_and_unit_conversion():
    f = T.tests().query("inv == 'FLEX'")
    assert len(f) == 274
    r1 = f.iloc[0]
    assert r1["p_atm"] == pytest.approx(757.7 / 760) and r1["o2"] == 0.21 and r1["fuel"] == "Methanol"
    assert f["fuel"].value_counts().to_dict() == {"Methanol": 157, "Heptane": 117}
    assert (f["p_atm"].dropna() > 0).all()
    assert any("pressure_zero_excluded" in x for x in f["flags"])         # FLEX test 114 has pressure 0


def test_cfig_bar_to_atm_and_blank_rows_dropped():
    c = T.tests().query("inv == 'CFIG'")
    assert len(c) == 333                                                  # 179 normal + 154 inverse (blank trailing rows dropped)
    row = c[(c["flame"] == "Normal")].iloc[0]
    assert row["p_atm"] == pytest.approx(0.9443956 / 1.01325)


def test_flex_composition_sums_support_o2_n2_co2_he_reading():
    rows, _, _ = T.read_table(T.TABLES / "PSI-69_Experimental table_FLEX.csv")
    ks = list(rows[0])
    sums = [sum(T.num(r[k]) or 0 for k in ks[6:10]) for r in rows if r[ks[0]]]
    assert 0.97 <= min(sums) and max(sums) <= 1.02


def test_solid_fuel_tables_have_no_pressure():
    s = T.tests().query("fuel_class == 'solid'")
    assert len(s) == 140 and s["p_atm"].notna().sum() == 0 and s["o2"].max() == pytest.approx(0.222)


def test_flags_are_kept_not_hidden():
    fl = A.quality_flags()
    assert "duplicate_test_id" in fl["FLEX"] and "ramped_flow_qualifier" in fl["FLAMEDESIGN"] and "o2_approximate" in fl["SAFFIRE2"]


# ---------- analytics ----------
def test_moon_zone_numbers():
    z = A.zone_stats()
    assert z["tests_in_zone"] == 66 and z["tests_with_o2_and_pressure"] == 989
    b = z["by_investigation"]
    assert (b["CFIG"]["in_zone"], b["FLAMEDESIGN"]["in_zone"], b["FLEX"]["in_zone"]) == (48, 18, 0)
    assert b["FLEX"]["o2_ge_30"] == 24 and b["FLEX"]["closest_psi_at_o2_ge_30"] == pytest.approx(10.33, abs=0.01)


def test_heatmap_totals_and_zone():
    h = A.heatmap()
    assert sum(map(sum, h["counts"])) == h["plotted"] == 989 and h["in_zone"] == 66 and h["o2_only_n"] == 161
    assert A.heatmap("FLEX")["in_zone"] == 0


def test_comparable_groups_guard_and_json_safe():
    for ds in ("flex", "cfig"):
        gs = A.comparable_groups(ds)
        assert any(g["chartable"] for g in gs) and any(not g["chartable"] for g in gs)
        for g in gs:
            if g["chartable"]:
                s = A.comparable_series(ds, g["key"])
                json.dumps(s, allow_nan=False)                            # no NaN leaks into the API
                assert s["n"] == g["n"] and len({p["src"] for p in s["points"]}) == s["n"]
            else:
                with pytest.raises(ValueError):
                    A.comparable_series(ds, g["key"])


def test_comparable_groups_do_not_mix_fuels_or_pressures():
    d = A.comparable_groups("flex")
    s = A.comparable_series("flex", d[0]["key"])
    f = T.tests().query("inv == 'FLEX'").set_index("psi_row")
    rows = f.loc[[p["src"] for p in s["points"]]]
    assert rows["fuel"].nunique() == 1 and rows["diluent"].nunique() == 1 and (rows["p_atm"].max() - rows["p_atm"].min()) < 0.1


# ---------- relevance engine ----------
def test_moon_scenario_ranks_flex_direct_strong_first():
    r = R.rank(MOON)
    assert r[0]["id"] == "FLEX" and r[0]["evidence"] == "Direct" and r[0]["band"].startswith("Strong") and r[0]["matches"]["both"] == 8


def test_solid_fuel_flips_flex_to_indirect_and_adds_gap():
    sc = dict(MOON, fuel="solid")
    by = {x["id"]: x for x in R.rank(sc)}
    assert by["FLEX"]["evidence"] == "Indirect" and by["BASS"]["evidence"] == "Direct"
    assert any("report oxygen but no pressure" in g for g in R.gaps(sc))


def test_missing_dimensions_excluded_not_matched():
    by = {x["id"]: x for x in R.rank(MOON)}
    assert "oxygen" in by["BASS"]["missing"] and by["BASS"]["coverage"] < by["FLEX"]["coverage"]
    assert next(d for d in by["FLEX"]["dims"] if d["name"] == "oxygen")["value"] == 1.0


def test_out_of_range_scores_zero_and_gap_reported():
    sc = dict(MOON, oxygen_pct=63)
    assert next(d for d in {x["id"]: x for x in R.rank(sc)}["FLEX"]["dims"] if d["name"] == "oxygen")["value"] == 0.0
    assert any("63" in g for g in R.gaps(sc))


def test_mismatch_and_weights():
    assert "mismatch" in R.mismatch(dict(MOON, gravity="mars")) and R.mismatch(MOON) == ""
    flat = R.rank(MOON, {"oxygen": 0, "pressure": 0, "fuel": 0, "gravity": 1, "objective": 0, "measurement": 0})
    assert all(x["score"] in (0.3,) or x["coverage"] > 0 for x in flat)


# ---------- copilot + Ollama ----------
class FakeOllama(BaseHTTPRequestHandler):
    seen = {}
    def log_message(self, *a): pass
    def do_GET(self):
        body = json.dumps({"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        FakeOllama.seen = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps({"message": {"content": FakeOllama.reply}}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)
    reply = "66 tests fall in the zone [D-ZONE-1] and FLEX has none [D-FAKE-9]."


@pytest.fixture
def ollama(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(copilot, "OLLAMA_HOST", f"http://127.0.0.1:{srv.server_port}")
    yield srv
    srv.shutdown()


def test_ollama_status_and_real_http_path(ollama):
    st = copilot.status()
    assert st["available"] and st["models"] == ["llama3.1:8b", "qwen2.5:7b"]
    out = copilot.answer("How many tests fall in the Moon base zone?", MOON, model="qwen2.5:7b")
    assert out["mode"] == "llm" and out["model"] == "qwen2.5:7b"
    assert FakeOllama.seen["model"] == "qwen2.5:7b" and FakeOllama.seen["stream"] is False and FakeOllama.seen["options"]["temperature"] == 0.1
    assert "Evidence:" in FakeOllama.seen["messages"][1]["content"] and "ONLY the evidence" in FakeOllama.seen["messages"][0]["content"]
    assert "D-FAKE-9" not in out["text"] and "[D-ZONE-1]" in out["text"] and any("unverifiable" in w for w in out["warnings"])


def test_copilot_works_without_ollama(monkeypatch):
    monkeypatch.setattr(copilot, "OLLAMA_HOST", "http://127.0.0.1:9")
    out = copilot.answer("What oxygen levels did FLEX test?", None)
    assert out["mode"] == "extractive" and out["sources"] and "FLEX" in out["text"] and out["warnings"]


def test_copilot_refuses_even_with_scenario():
    out = copilot.answer("zebra quantum banana", MOON, llm=lambda s, p: "should not be called")
    assert out["mode"] == "refusal" and out["sources"] == []


def test_copilot_llm_failure_falls_back_and_uncited_flagged():
    def boom(s, p): raise RuntimeError("model crashed")
    assert copilot.answer("FLEX suppressant pressure", None, llm=boom)["mode"] == "extractive"
    out = copilot.answer("FLEX suppressant pressure", None, llm=lambda s, p: "FLEX is great.")
    assert any("no evidence" in w for w in out["warnings"])


def test_box_fact_is_computed_not_invented():
    f = copilot.box_fact(MOON)
    assert f["id"] == "D-BOX" and "8 tests" in f["text"] and "FLEX 8" in f["text"] and copilot.box_fact(dict(MOON, oxygen_pct=None)) is None


# ---------- PDF ----------
def test_pdf_briefing_content():
    pdf = briefing.build(MOON)
    r = PdfReader(io.BytesIO(pdf)); text = " ".join(p.extract_text() for p in r.pages)
    assert pdf[:4] == b"%PDF" and len(r.pages) >= 2
    for needle in ("FLARE-X Evidence Briefing", "66 of 989", "Moon-base reference zone", "Research gaps", "Citations", "PSI-69", "10.60555/mbq8-0451", "SHA-256", "not a fire-risk prediction"):
        assert needle in text, needle
    assert "safe/unsafe" not in text.lower()


def test_pdf_mismatch_and_unicode_safe():
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(briefing.build(dict(MOON, gravity="mars")))).pages)
    assert "WARNING" in text and "mismatch" in text
    assert briefing.safe("O\u2082 \u2265 30\u2013100 & <b>") == "O2 &gt;= 30-100 &amp; &lt;b&gt;"


# ---------- API ----------
def test_api_endpoints():
    assert client.get("/api/health").json() == {"ok": True, "tests": 1161, "tables": 22}
    m = client.get("/api/meta").json(); assert m["tests_in_zone"] == 66 and m["investigations"] == 19
    r = client.post("/api/rank", json=MOON).json(); assert r["results"][0]["id"] == "FLEX" and r["gaps"]
    assert len(client.get("/api/presets").json()) == 4 and len(client.get("/api/story").json()["timeline"]) == 5
    assert client.get("/api/heatmap?inv=CFIG").json()["in_zone"] == 48
    p = client.post("/api/briefing.pdf", json=MOON); assert p.status_code == 200 and p.headers["content-type"] == "application/pdf" and "attachment" in p.headers["content-disposition"]
    assert "<title>FLARE-X" in client.get("/").text


def test_api_validation():
    assert client.post("/api/rank", json=dict(MOON, oxygen_pct=140)).status_code == 422
    assert client.post("/api/rank", json=dict(MOON, pressure_psi=-1)).status_code == 422
    assert client.post("/api/rank", json=dict(MOON, concern="drop table")).status_code == 422
    assert client.post("/api/copilot", json={"question": "x"}).status_code == 422
    assert client.get("/api/charts/series?dataset=flex&key=Methanol|O2/N2|0.5").status_code == 422
    assert client.get("/api/charts/series?dataset=nope&key=a").status_code == 422
    assert client.get("/api/charts/series?dataset=flex&key=bad").status_code == 422


def test_catalog_integrity():
    for r in catalog.records():
        assert r["psi"].startswith("PSI-") and r["links"][0]["url"].endswith(r["psi"]) and r["limitation"] and r["note"]
        assert all((T.TABLES / f).exists() for f in r["tables"])
    assert {t for r in catalog.records() for t in r["tables"]} == {m["file"] for m in T.manifest() if "PSI-142" not in m["file"]}


# ---------- hosted mode + design hooks ----------
def test_hosted_flag_reaches_the_ui(monkeypatch):
    monkeypatch.setattr(copilot, "OLLAMA_HOST", "http://127.0.0.1:9")
    monkeypatch.setattr(copilot, "HOSTED", True)
    st = client.get("/api/ai/status").json()
    assert st["available"] is False and st["hosted"] is True


def test_galaxy_is_wired_into_every_page():
    html = (T.TABLES.parent.parent / "web" / "index.html").read_text(encoding="utf-8")
    assert html.index("galaxy.js") < html.index("app.js")                  # canvas exists before the app renders
    assert client.get("/galaxy.js").status_code == 200 and "#galaxy" in client.get("/style.css").text


def test_deploy_files_present():
    root = T.TABLES.parent.parent
    for f in ("Dockerfile", "render.yaml", ".gitignore", ".github/workflows/ci.yml", "requirements.txt", "requirements-dev.txt"):
        assert (root / f).exists(), f
    assert "pytest" not in (root / "requirements.txt").read_text()          # test tools stay out of the deployed image
