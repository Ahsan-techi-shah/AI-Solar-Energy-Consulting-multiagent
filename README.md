# ☀️ SolarAI — Multi-Agent Solar Engineering Consultant

SolarAI is a Streamlit + CrewAI application that uses a team of specialized AI agents with a Groq-hosted LLM to create a conceptual residential solar engineering proposal.

## Architecture

- Streamlit — user interface
- CrewAI — multi-agent orchestration
- Groq — LLM provider
- `openai/gpt-oss-120b` — selected model
- Python calculation functions — deterministic engineering calculations

## Project structure

```
app.py               Streamlit UI
solar_crew.py        Agents, tasks and crew runner
solar_tools.py       Deterministic calculations
requirements.txt
```

## Agents

1. Electrical Load Engineer
2. Solar Design Engineer
3. Battery Engineer
4. Financial Analyst
5. Safety Engineer
6. Chief Solar Engineer

## Deploy on Streamlit Community Cloud

1. Upload this repository to GitHub with `app.py` at the repo root.
2. Open Streamlit Community Cloud and connect your GitHub account.
3. Select the repository and `app.py`.
4. In Advanced settings, choose Python 3.11 or 3.12.
5. In Advanced settings → Secrets, add:

```toml
GROQ_API_KEY = "your_groq_api_key"
```

6. Deploy.

Do not commit your API key to GitHub.

## Important engineering note

This is a conceptual decision-support/demo application. Final PV sizing, string configuration, protection, cable sizing, equipment selection, tariffs, and installation must be verified against actual manufacturer datasheets, site conditions, applicable standards, and qualified engineering practice.
