from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import analytics, briefing, catalog, copilot, relevance, tables
from .config import WEB, RETRIEVED

app = FastAPI(title="FLARE-X", version="1.0")


class Scenario(BaseModel):
    environment: Literal["spacecraft", "lunar", "mars", "rover"] = "lunar"
    concern: Literal["suppression", "prevention", "detection", "gas-phase"] = "suppression"
    gravity: Literal["micro", "lunar", "mars", "normal"] = "lunar"
    fuel: Literal["any", "solid", "liquid", "gas"] = "any"
    oxygen_pct: Optional[float] = Field(None, ge=0, le=100)
    pressure_psi: Optional[float] = Field(None, gt=0, le=100)
    weights: Optional[dict] = None

    def sc(self):
        return self.model_dump(exclude={"weights"})


class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    scenario: Optional[Scenario] = None
    model: Optional[str] = None


@app.get("/api/health")
def health():
    return {"ok": True, "tests": int(len(tables.tests())), "tables": len(tables.manifest())}


@app.get("/api/meta")
def meta():
    z = analytics.zone_stats()
    return {"retrieved": RETRIEVED, "tables": len(tables.manifest()), "table_rows": sum(m["rows"] for m in tables.manifest()), "bytes": sum(m["bytes"] for m in tables.manifest()),
            "investigations": len(catalog.records()), "tests": z["tests_total"], "tests_with_o2_and_pressure": z["tests_with_o2_and_pressure"],
            "tests_in_zone": z["tests_in_zone"], "zone": z["zone"], "solid": z["solid"], "by_investigation": z["by_investigation"], "resources": catalog.context()["resources"]}


@app.get("/api/investigations")
def investigations():
    return catalog.records()


@app.get("/api/tables")
def tables_manifest():
    return tables.manifest()


@app.get("/api/presets")
def presets():
    return catalog.context()["presets"]


@app.get("/api/story")
def story():
    c = catalog.context()
    return {"timeline": c["timeline"], "earth": c["earth"]}


@app.post("/api/rank")
def rank(s: Scenario):
    return {"scenario": s.sc(), "mismatch": relevance.mismatch(s.sc()), "results": relevance.rank(s.sc(), s.weights), "gaps": relevance.gaps(s.sc())}


@app.get("/api/heatmap")
def heatmap(inv: str = "all"):
    return analytics.heatmap(inv)


@app.get("/api/charts/groups")
def groups(dataset: Literal["flex", "cfig"] = "flex"):
    return {"groups": analytics.comparable_groups(dataset), "min_points": analytics.MIN_GROUP, "flags": analytics.quality_flags()}


@app.get("/api/charts/series")
def series(dataset: Literal["flex", "cfig"], key: str = Query(...)):
    try:
        return analytics.comparable_series(dataset, key)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/ai/status")
def ai_status():
    return copilot.status()


@app.post("/api/copilot")
def ask(a: Ask):
    return copilot.answer(a.question, a.scenario.sc() if a.scenario else None, a.model)


@app.post("/api/briefing.pdf")
def pdf(s: Scenario):
    return Response(briefing.build(s.sc()), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="flarex_briefing.pdf"'})


app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
