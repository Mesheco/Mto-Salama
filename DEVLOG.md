# Mto Salama - Development Log

Built for SafeSpace Hacks (build window 17 Oct - 22 Nov 2026). One line per work day.

| Date | What I built / learned |
| --- | --- |
| 2026-10-27 | Project set up: repo, environment, data check script. Demo crossing (fictional, Makueni-style) defined. |
| 2026-10-28 | Switched to Claude API + Jac/byLLM. First agent pipeline (agents.jac): Listener, Fusion, Skeptic, Messenger on a crossing graph. Offline demo mode and AI-offline fallback both work. |
| 2026-10-28 | Phase 1 first screen: Streamlit app (status board, reasons, bilingual draft alert, approve, "I disagree" override with log). Live upstream rain fetcher. Keyword backup reader. Normal / confusing / failure test cases all pass. |
| 2026-10-29 | Set up GitHub repo. ML surge predictor: history download (Nyando + Athi, 2000-2025), Random Forest trained on rain features, tested on unseen years, plain-language explanations. Fusion agent now uses the model, with rain rules as fallback. |
| 2026-10-30 | Downloaded real history and trained the surge model: ROC AUC 0.84 on unseen years (2019-2025); CAUTION catches 78% of surges. Tested longer rain windows - they made it worse (wetter recent years), so kept short windows. |
| 2026-10-31 | Deployed the app on Streamlit Community Cloud (offline mode when no API key). Built our own offline NLP Listener (260 synthetic Kiswahili/Sheng/English messages): ~79% realistic accuracy; safety guard halves "rising water read as all clear" (22% -> 12%). Claude now only reads messages the NLP model is unsure about. |
| 2026-11-09 | Polish for clarity and accessibility: "How it works" panel, a clear action line under each status, Nairobi-time stamp on every check, read-aloud buttons (browser text-to-speech, Kiswahili and English), screen-reader alert on the status card. Checked at phone and laptop width. |
| 2026-11-14 | Drafted the Devpost page. Added the "Report from the river" page: anonymous reports (phone numbers removed, 24-hour keep, spam limit) that flow into the leader's check - closing the loop from villager to leader. Renamed demo scenarios to plain stories. |
