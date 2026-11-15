# FLARE-X — Space Combustion Research Intelligence

An evidence-first scientific research platform exploring NASA's microgravity combustion experiments and their relevance to future space habitats.

Built for the 2026 NASA Space Apps Challenge, *Flame in Freefall*.

FLARE-X evaluates the relevance and coverage of available experimental evidence for mission scenarios. It is not a fire-risk predictor, safety certification, or operational decision-support system.

## Run locally (Python 3.12)

```bash
pip install -r requirements-dev.txt
python run.py
```

Open http://127.0.0.1:8000 in your browser.

Run the tests:

```bash
python -m pytest -q
```

## Enable the AI Copilot (Ollama)

FLARE-X can use a locally running Ollama model for AI-generated responses.

```bash
ollama pull llama3.1:8b
ollama serve
```

Other Ollama-compatible chat models may also work, depending on their capabilities and available resources.

Reload the **AI Copilot** page. When Ollama is available and a model is installed, the status indicator becomes active and a model picker appears.

Optional environment variables:

- `OLLAMA_HOST`: Ollama server address (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: preferred model name

Pre-download the model and test its performance on your machine before a demonstration.

If Ollama is unavailable, the Copilot falls back to retrieved scientific evidence.

### Scientific citation limitations

The Copilot validates citation IDs against retrieved evidence. This prevents references to unavailable sources, but does not guarantee that every generated claim is semantically supported.

Always verify scientific conclusions against the cited records.

## Platform features

| Page | Description |
|---|---|
| Every page | Animated galaxy background with stars, nebula, spiral galaxy, shooting stars and blue flame sphere |
| Home | Live headline statistics computed from the experimental data |
| Investigations | 19 experiment records with computed ranges, limitations and source references |
| Compare | Side-by-side experiment comparison showing similarities, differences and unreported parameters |
| Mission Simulator | Scenario presets, evidence relevance ranking, coverage map, research gaps and PDF briefing |
| Data & Coverage | Oxygen-pressure heatmap, comparable-test scatter charts and data-quality indicators |
| AI Copilot | BM25-based retrieval, computed facts, local Ollama integration, citation validation and evidence-aware responses |
| Earth Applications | Examples of terrestrial applications inspired by space research |
| Why It Matters | Historical spaceflight incidents and future exploration context |

### Evidence relevance scoring

The mission simulator uses adjustable weights:

| Dimension | Weight |
|---|---:|
| Oxygen | 0.25 |
| Pressure | 0.20 |
| Fuel | 0.20 |
| Gravity | 0.15 |
| Objective | 0.10 |
| Measurement | 0.10 |

Oxygen conditions are matched within ±3 percentage points and pressure within ±10%.

At least three matching tests receive a score of 1; one or two matching tests receive 0.5.

Dimensions without available data are excluded from the score and reported as evidence coverage gaps, rather than being treated as successful matches.

Results are organised by evidence type (Direct, Indirect, Gap), then by relevance score.

These weights are transparent project-defined heuristics, not a validated NASA methodology or operational safety assessment.

## Experimental data

See [`docs/DATA_MANIFEST.md`](docs/DATA_MANIFEST.md) for the dataset inventory, sources and processing notes.

The project includes 22 NASA Physical Sciences Informatics (PSI) experimental tables:

- 211 KB of experimental data
- 2,009 rows
- 1,161 parsed tests

The original table files are stored in `data/psi_tables/`.

To refresh the tables:

```bash
python scripts/psi_tables.py
```

The script downloads the small experimental tables, not the multi-gigabyte archives.

Please consult the data manifest and original NASA PSI investigation records when reusing the datasets. Their applicable notices and conditions take precedence over the FLARE-X software licence.

## Known scientific limitations

- FLEX composition headers are labelled `O/N/CO/He`. The project interprets them as O2/N2/CO2/He; row sums between 0.98 and 1.01 support this interpretation.
- FLEX-2's table lists planned ranges rather than measurements. It is not treated as experimental test data.
- Only FLEX, CFI, CFI-G and Flame Design report both oxygen and pressure per test.
- Solid-fuel tables generally lack pressure measurements; BASS has no reported conditions.
- The "Moon-base zone" (30% O2 or more, 10.2 psi or less) is a reference scenario defined in the Space Apps challenge brief. It is not a validated habitat atmosphere specification.
- The available PSI dataset does not establish actual fire behaviour under lunar or Martian partial gravity.
- The ISS preset (21% O2, 14.7 psi) represents an assumed typical cabin atmosphere.
- Relevance measures similarity to documented experimental conditions; it does not predict fire behaviour. Droplet and gas-flame results must not be transferred directly to solid-material fires.
- Retrieval currently uses keyword-based BM25 search. Embedding-based retrieval could be introduced as a future enhancement.
- FLARE-X does not use the NASA logo and is not affiliated with or endorsed by NASA. Check event rules concerning pre-event development with your Local Lead before submission.

## Technology and architecture

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **Data processing:** Pandas, NumPy
- **Scientific data:** NASA PSI experimental tables
- **AI inference:** Ollama (local deployment)
- **Retrieval:** BM25
- **Reporting:** PDF generation with ReportLab
- **Testing:** Pytest
- **Deployment:** Docker and Render

## Contributing

Contributions and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and run the tests.
4. Submit a pull request describing your contribution.

The included GitHub Actions workflow runs the test suite on pushes and pull requests.

## Licence

FLARE-X software is distributed under the MIT License. See the [`LICENSE`](LICENSE) file.

The licence applies to the project's original software. NASA datasets and third-party materials remain subject to their respective terms and attribution requirements.

## Deploy a public demo

FLARE-X combines a Python backend with a static frontend. GitHub Pages alone cannot host the complete application.

### Render

1. Push the repository to GitHub.
2. Open Render and select **New → Blueprint**.
3. Connect your repository.
4. Render uses the included `render.yaml` configuration.

The free plan may suspend inactive services, so allow time for the application to start before a demonstration.

### Docker

Build and run the application:

```bash
docker build -t flarex .
docker run -p 8000:8000 flarex
```

The container honours the `PORT` environment variable.

### Hosted AI limitations

When `FLAREX_HOSTED=1`, local Ollama access is disabled.

The deployed application currently provides retrieval-based responses. A separately configured hosted inference provider is required to enable generative AI on the public website.

Do not expose a personal Ollama instance directly to the internet. It does not provide the access controls needed for a public deployment.

The current application does not implement user accounts or persistent user data storage.