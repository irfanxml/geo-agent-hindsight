# GEO Visibility Agent

A single-folder demo of the scan → Hindsight memory → recommendation loop. It combines the AI pipeline, the Hindsight-compatible memory layer, and the React dashboard from the supplied ZIP. The data contracts match the team document and the project brief.

## 🛠️ Installation Instructions

**1. Clone and Setup Backend (Terminal 1)**
Open a terminal and set up the Python environment:
```bash
python -m venv .venv
# On Windows PowerShell: .\.venv\Scripts\Activate.ps1
# On Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

**2. Configure API Keys**
Copy the placeholder environment file to activate the integrations:
```bash
cp .env.example .env
```
Open `.env` and add your valid `GROQ_API_KEY`, `TAVILY_API_KEY`, and `SERPER_API_KEY`. (Ensure `MOCK_MODE=0` is set if you want real-time live data). To enable remote Hindsight memory, also add your `HINDSIGHT_API_KEY`!

**3. Start the Backend API**
```bash
python -m integration.api
```

**4. Start the Frontend Dashboard (Terminal 2)**
Open a *second* terminal window in the project folder and run:
```bash
cd frontend
npm install
npm run dev
```
Open the local URL printed by Vite (usually `http://localhost:5173`) to view the application!

Open the local URL printed by Vite. You can edit the brand and category, then click **Run visibility scan**. The dashboard calls the Python API, which scans, reads that brand's history, creates a recommendation, and saves the new scan to `hindsight_memory/data/`. The visibility chart, mention rate, competitor ranking, queries, and recommendation all refresh from that response and saved history.

To fill the Hindsight timeline, use its action form after a live scan. Record the action you actually tried, what happened, and the observed mention change. That record is saved for that brand and feeds the recommendation on its next scan. An empty timeline means no actions have been logged yet.

Scan and action history and saved recommendations are stored locally in `hindsight_memory/data/` so the recommendation agent can learn across scans. Dashboard reloads use the saved recommendation and do not call Groq again. To clear all saved local test history and start fresh, stop the Python API and run this from the project root:

```powershell
python -m hindsight_memory.reset_history --brand Keka
```

Pass `--brand Keka` to clear only Keka's saved scan/action history and recommendation cache. Omit `--brand Keka` to clear all brands. This does not delete source fixtures or change provider settings.

Mock mode needs no API keys and uses simulated evidence so repeated demo scans visibly change. Those simulated mention and competitor numbers are for demonstrating the workflow, not measurements from live search. To use live evidence, configure the provider keys below.

Mock competitors now come from the brand/category peer catalog in `ai_pipeline/competitor_catalog.py` (for example, Chanel gets luxury peers and Notion gets project-management peers). In live mode the analysis prompt only counts comparable brands found in search evidence. For a category not covered by the demo catalog, mock mode reports no competitor instead of inventing an unrelated one.

Run the pipeline smoke check from the project root with `python smoke_test.py`. For a command-line scan without the UI, run `python -m integration.pipeline --brand Notion --category "project management software"`.

## Use live providers

Copy `.env.example` to `.env`, add valid Groq, Tavily, and Serper keys, and install requirements. The example selects `MOCK_MODE=0`; the Python API loads the project-root `.env` before choosing a mode. Restart the Python API after changing `.env`. The health badge reports whether live provider keys are ready, and a scan explains which integration is missing rather than silently falling back to mock output. A live scan uses Groq for query generation, evidence analysis, and recommendations, and Tavily plus Serper for web evidence. Search calls run concurrently; Groq analysis is paced, evidence and memory prompts are compact, and 429 responses respect Groq's retry delay. Keep `.env` private. Remote Hindsight storage is optional; without its URL and key, the memory layer uses local JSON files. To enable the remote service, also install `hindsight-client` and set `HINDSIGHT_API_URL` and `HINDSIGHT_API_KEY`.

Without a `.env`, the app defaults to mock mode for a no-key preview. Mock scan scores are capped below 100% and use category-appropriate demo peers where available. They are simulated examples, not live measurements.

## Project map

- `ai_pipeline/`: scan and recommendation agents with shared JSON contracts.
- `hindsight_memory/`: local JSON history plus optional Hindsight service integration.
- `frontend/`: React + TypeScript staged-data dashboard.
- `integration/`: end-to-end pipeline entry point and mock smoke check.
- `fixtures/`: scan 1, 5, and 10 contract examples.

The supplied ZIP's `.env` files and Python bytecode were left out. Start with `.env.example` if you need live integrations.

## 🧠 Hindsight Integration Explained
The `hindsight_memory` module forms the underlying "Long-Term Memory" layer for this GEO Agent. It connects to the Vectorize Hindsight API to give the AI context over time rather than treating every scan in a vacuum.

**How it works seamlessly in the pipeline:**
1. **Persistent Context:** Every time a new brand scan finishes, or a marketing action is logged, it is permanently written into a local JSON mirror and `Hindsight.retain()` is called to index that snippet in a secure Vector Bank.
2. **AI Action Reflection:** Instead of naively returning random tips, when the Pipeline asks for a recommendation, the memory module runs `find_similar_precedent()`.
3. **Situational Awareness:** By querying the Hindsight embeddings securely, the module maps the brand's *current visibility deficit* back to historical campaigns across the agency's index. If adding "Schema.org FAQ pages" raised visibility from 20% to 50% last month, Hindsight flags this identical pattern constraint, enabling the Recommendation Agent to synthesize exact, proven strategies.

This provides the GEO Agent with compounding intelligence: the more actions you take, the smarter its next set of actions becomes!
