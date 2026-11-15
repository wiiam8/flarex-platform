# 3-minute demo (numbers are computed from the real PSI tables; re-check them live on the Home page)

**0:00 Problem (Home page, 20 s).** "NASA has decades of microgravity combustion data, but it is hard to see what it actually covers. FLARE-X parsed 22 PSI tables, 1,161 tests, and shows where the evidence ends."

**0:20 The gap (Home, 20 s).** Point at the three cards: "Only 66 of 989 tests that report both oxygen and pressure fall in the planned Moon-base atmosphere, and every one is a gas flame. FLEX, the main suppression dataset, gets as close as 10.33 psi but never inside. Solid fuels: 0 of 140 tests even report a pressure."

**0:40 Scenario (Mission simulator, 40 s).** Click **Moon base**. "FLEX ranks first: direct evidence, strong, 8 tests near 30% oxygen and 10.2 psi. BASS is direct for solids but low coverage, because its table has no conditions. FLARE-X shows coverage separately and never counts missing data as a match." Open **Why this score** on FLEX.

**1:20 Map + gaps (same page, 25 s).** "The white cross is our scenario; the red box is the Moon-base zone." Read the gaps list. Switch **Fuel class** to Solid: FLEX flips to indirect, and the pressure gap appears.

**1:45 Catch bad inputs (10 s).** Set gravity to Mars with a lunar habitat: mismatch warning.

**1:55 Comparable tests (Data & coverage, 25 s).** "We only chart tests that share fuel, atmosphere and pressure." Show a FLEX group, then point at a greyed-out group: "too few comparable tests, so we refuse to chart them."

**2:20 AI copilot (30 s).** Ask "How many tests fall in the Moon-base zone?" Show the cited answer and open the evidence list. Then ask a nonsense question: it refuses. "It runs on local Ollama; every citation is checked."

**2:50 Impact (10 s).** Download the PDF briefing. Close on **Why it matters** (Apollo 1, Apollo 13, Mir) and **Earth applications**.

**Backup if Ollama is down:** the copilot falls back to retrieved evidence automatically. Say so; it is a feature.
