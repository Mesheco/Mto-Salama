# Credits

## Data
- Weather and historical rainfall: Open-Meteo (https://open-meteo.com), CC BY 4.0
- River discharge (2000-2025, used to train the surge model): Open-Meteo Flood API, based on
  GloFAS - Copernicus Emergency Management Service
- Community messages (`data/messages*.csv`): synthetic, written for this project. No real people's data.
- Demo crossing "Mto Kavuthu drift": fictional, modelled on Makueni seasonal river crossings.

## AI, language and libraries
- LLM (optional): Claude Haiku 5.5 via the Anthropic Claude API
- Jac programming language and byLLM (Jaseci Labs, open source) - agent pipeline
- scikit-learn (Random Forest, TF-IDF, logistic regression), pandas, joblib, requests, Streamlit
- Hosting: Streamlit Community Cloud

## Safety guidance referenced
- Kenya Red Cross and Kenya Meteorological Department public advisories

## AI assistance
- Claude (Anthropic): project planning, code generation and review, synthetic message drafting

## Built during the event (17 Oct - 22 Nov 2026)
All project code, models and data files in this repository were created during the event.
See DEVLOG.md and the dated commit history. Pre-existing components are the open-source
libraries, Jac/byLLM, the Claude API and the Open-Meteo/GloFAS data listed above.
