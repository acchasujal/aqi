# EXP-015 root-cause prioritization

This ranking was set from provenance and validation audits before interpreting the new sensitivity results.

| Rank | Issue | Evidence and likely impact | Safe EXP-015 action |
|---:|---|---|---|
| 1 | Extreme historical labels and repeated scoring | EXP-013/014 full RMSE is almost entirely a few very large readings, some reused under multiple origins. This destabilizes model selection, without proving labels wrong. | Quantify unique events, contribution, and ordinary-range diagnostic; retain every label in primary RMSE. |
| 2 | Private forecast lead mismatch | Legacy short-gap validation differs from the live 193–240-hour private PM lead. | Evaluate public/private separately on EXP-014's competition-shaped rows. |
| 3 | Insufficient independent confirmation | EXP-013 fully reuses EXP-012 station-hours and EXP-014 reports overlap. | Treat new results as exploratory; await genuinely new official labels for confirmation. |
| 4 | Malad Mindspace pooling | Separate coordinates establish a real physical-site mismatch; 8,120 historical rows enter the substring feature. | Test a single opt-in exclusion of Mindspace on matched rows. Do not alter default. |
| 5 | Archive hour semantics | The original assumption is unverified, with possible hour-of-day signal. | Compare ±1-hour shifts as *diagnostic hypotheses only*. Do not promote a shift without source documentation. |
| 6 | 2024 leap-day matching | EXP-011 confirmed the day-of-year defect but did not find sufficient evidence for replacing W50. | Cite its matched result; do not combine it with another change. |

The only proposed provenance correction is removing Mindspace from Malad's historical pool. Same-coordinate Borivali/Malad series remain ambiguous; choosing among them by score would be unsupported. The two shift sensitivities are not model candidates eligible for promotion because timestamp interpretation is unresolved. No supervised search, blend-weight tuning, target cleaning, or production change is planned.
