# Surge predictor - results

Rivers: athi, nyando. Trained on 2000-01-01 to 2014-12-31; scored on 5112 days the model never saw (643 surge days).

| Alert level | Probability | Surges caught (recall) | Alerts that were right (precision) | Calm days wrongly flagged |
| --- | --- | --- | --- | --- |
| CAUTION | >= 38% | 78% | 32% | 23% |
| DO NOT CROSS | >= 74% | 32% | 37% | 8% |

ROC AUC on unseen years: 0.84

What the model relies on most:

- upstream rain in the last 3 days: 20%
- upstream rain in the last 7 days: 17%
- time of year: 16%
- upstream rain in the last 14 days (wet ground): 16%
- rain at the wettest upstream point (3 days): 15%
- upstream rain today: 8%
- long rains season: 4%
- short rains season: 3%

Missing a surge is the costly mistake, so thresholds favour catching surges over avoiding false alarms. Flow is modelled (GloFAS), not measured.
