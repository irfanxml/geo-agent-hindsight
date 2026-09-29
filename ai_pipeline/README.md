# GEO Visibility Agent — AI Pipeline

This project contains two independent Python modules for the hackathon:

- **`scan_agent.py`** generates mostly non-branded category questions, searches
  each query with Tavily and Serper, sends the combined evidence to Groq for
  analysis, and returns the locked Scan Result contract.
- **`recommendation_agent.py`** compares a current scan with the Hindsight-shaped
  history and returns one increasingly specific recommendation.
- **`llm.py`** is the only module that communicates with an LLM. It uses the
  OpenAI-compatible client pointed at Groq. Both agents import `call_llm`
  instead of creating model clients themselves.
- **`fake_data.py`** provides realistic Scan 1, Scan 5, and Scan 10 memory
  records without requiring the Hindsight teammate.
- **`run_tests.py`** exercises both agents and contract validation.

## Run locally in mock mode

Mock mode needs no API key or third-party package:

```bash
MOCK_MODE=1 python run_tests.py
MOCK_MODE=1 python scan_agent.py "Notion" "Project management software"
```

The mock path is deterministic and intentionally includes different visibility
levels and historical outcomes so the Scan 1 → Scan 5 → Scan 10 recommendation
gets more specific.

## Run with Groq, Tavily, and Serper

Install the only real-mode dependency:

```bash
pip install -r requirements.txt
```

Set the required environment variables:

```bash
export GROQ_API_KEY="your-groq-key"
export GROQ_MODEL="openai/gpt-oss-120b"
export TAVILY_API_KEY="your-tavily-key"
export SERPER_API_KEY="your-serper-key"
export MOCK_MODE="0"
python scan_agent.py "Notion" "Project management software"
```

The same variables are listed in `.env.example`. The project loads credentials
from the project-root `.env` file or the process environment; it does not
hardcode credentials. The retired starter model ID is automatically migrated
to `openai/gpt-oss-120b`.

For every generated query in real mode, the Scan Agent performs one Tavily
search and one Serper search, then sends both result sets to Groq for brand,
competitor, and evidence analysis. Tavily and Serper data remains internal;
the Scan Result JSON contract does not change.

## Import the modules

```python
from scan_agent import run_scan
from recommendation_agent import get_recommendation

current_scan = run_scan("Notion", "project management software")
memory_record = {
    "brand": "Notion",
    "scan_history": [],
    "actions_log": [],
}
recommendation = get_recommendation(current_scan, memory_record)
```

`memory_record` must use the exact Hindsight input shape. Historical scans must
use the exact Scan Result shape returned by `run_scan`.

## Hindsight teammate integration

`integration_example.py` shows the intended boundary: Hindsight supplies the
current scan and its memory record, while the Recommendation Agent returns the
locked recommendation object. It does not store data or implement a Hindsight
client.

```python
from integration_example import recommend_from_hindsight

recommendation = recommend_from_hindsight(current_scan, memory_record)
```

For JSON fixtures, run:

```bash
MOCK_MODE=1 python integration_example.py current_scan.json memory_record.json
```

Ready-to-use fixtures are included for all three milestones:

```bash
MOCK_MODE=1 python integration_example.py \
  fixtures/scan_5/current_scan.json \
  fixtures/scan_5/memory_record.json
```

The corresponding `fixtures/scan_1/` and `fixtures/scan_10/` directories
exercise the baseline and mature-history cases.

## Contracts and validation

The agents reject missing, renamed, extra, or incorrectly typed fields. They
also validate ISO8601 timestamps, query counts, mention bounds, brand matching,
historical action references, and recommendation scan numbers. JSON responses
wrapped in markdown fences are accepted; malformed model output is retried once
and then raises an error instead of becoming silent invalid data.
