# Listener (NLP) - results

Trained on 260 synthetic messages in Kiswahili, Sheng and English (no real people's messages).

| Measure | Result |
| --- | --- |
| Realistic accuracy (cross-validation) | 79% (model) / 80% (with safety guard) |
| Messages the model is confident about | 84% |
| Accuracy when confident | 85% |
| Rising water misread as 'all clear' | 22% (model) / 12% (with safety guard) |

The safety guard stops messages with clear danger words (imejaa, inapanda, mafuriko, rising, flood...) from being read as 'all clear' unless they are negated. Messages below 45% confidence are passed to Claude when an AI key is set, or marked as unsure. An 'all clear' report never lowers the warning, and one report alone can raise the status to CAUTION at most (DO NOT CROSS needs heavy upstream rain or two or more reports), so a single misread message cannot make the app say 'safe' or trigger DO NOT CROSS.
