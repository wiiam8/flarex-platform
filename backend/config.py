import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TABLES = DATA / "psi_tables"
WEB = ROOT / "web"
RETRIEVED = "2026-11-14"
PSI_PER_ATM, MMHG_PER_ATM, BAR_PER_ATM = 14.696, 760.0, 1.01325
MOON_O2, MOON_P_PSI = 0.30, 10.2          # challenge description: 30% O2 or more, 10.2 psi or less
O2_TOL, P_TOL = 0.03, 0.10                # scoring tolerance: +-3 percentage points O2, +-10% pressure
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
HOSTED = os.getenv("FLAREX_HOSTED", "") == "1"      # set on a public deployment: no local Ollama there
