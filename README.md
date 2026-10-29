# Mto Salama (Safe River)

Multi-agent AI that warns local leaders when **rain upstream** makes a seasonal river
crossing dangerous - even when it is dry and sunny at the crossing.

> Prototype for SafeSpace Hacks 2026. It supports official warnings; it does not replace
> the Kenya Meteorological Department, county authorities or emergency services (1199).

## How it works

| Agent | Type | Job |
|---|---|---|
| Listener | Claude (byLLM) + keyword backup | Reads Kiswahili / Sheng / English community messages |
| Surge model | Machine learning (Random Forest) | Predicts tomorrow's surge from upstream rain; explains why |
| Fusion | Rules (code) | Combines the surge model with community reports |
| Skeptic | Rules (code) | Flags missing or old data and disagreements; never says "safe" |
| Messenger | Claude (byLLM) + template backup | Drafts a short bilingual SMS alert |

A local leader approves the alert or overrides it with a reason (logged).

## Run it (Windows, VS Code terminal)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Free demo (no key): set `MTO_MODEL=mockllm` in `.env`, then:

```
streamlit run app.py        # the app in your browser
jac run agents.jac          # the agents in the terminal
```

With Claude: put your key in `.env` and set `MTO_MODEL=anthropic/claude-haiku-5-5`.

## Train the surge model

```
python -m ml.download_history   # ~25 years of rain + river flow (Open-Meteo / GloFAS)
python -m ml.train              # trains, tests on unseen years, writes models/report.md
```

Without a trained model the app falls back to simple rain rules.

## Files

- `agents.jac` - the four-agent pipeline (Jac language, graph + walker)
- `app.py` - Streamlit screen
- `weather.py` - live upstream rainfall (Open-Meteo)
- `ml/` - surge predictor: features, history download, training, prediction
- `crossings.json` - the fictional demo crossing and its upstream points
- `check_data.py`, `check_ai.py` - setup checks

## Limitations

Rainfall and river models are coarse (about 5 km for river flow) and can miss small
seasonal streams. Community reports help fill that gap, but the tool can be wrong -
people should always look at the water and follow official warnings.

See `CREDITS.md` for data, tools and AI assistance.
