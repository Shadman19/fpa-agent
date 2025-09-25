# FP&A CFO Copilot — GitHub Repo

A Streamlit app that answers CFO questions from monthly finance CSVs.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Run tests
```bash
pytest -q
```

## Deploy to Hugging Face (optional)
You can push this same repo to a Hugging Face Space:
1. Create a Space (Streamlit, Python 3.11).
2. `git remote add hf https://huggingface.co/spaces/<user>/fpa-cfo-copilot`
3. `git push -u hf main`

## Repo structure
- `app.py` — UI + charts
- `agent/planner.py` — intent parser
- `agent/tools.py` — metrics (FX, GM%, Opex, EBITDA, runway)
- `fixtures/` — demo CSVs and offline fallback
- `tests/` — sanity tests
- `.github/workflows/python-tests.yml` — CI on push/PR
