# EXP-008 — Model recommendation

## INCONCLUSIVE

No corrected source-aware candidate was evaluated. The current `hist24_blend50_median72` remains unchanged as the repository's existing candidate; this audit does not validate it. Evidence confirms that the current substring matcher pools a nearby but distinct Mindspace-Malad station into Malad West and multiple historical series for Borivali/Malad. Because the appropriate target series cannot be uniquely established from the provided metadata, choosing one by completeness or validation performance would violate the task's provenance requirement.

Do not promote any EXP-008 feature change. The production model selection and prediction code were not modified. EXP-007's prior result remains historical evidence under its original mapping and assumptions, not a corrected result.

Resume only after obtaining source-owner identity and interval documentation, or redesign as explicitly labeled sensitivity analysis without claiming a verified target mapping.

The separate validation/inference fallback mismatch is confirmed and tracked for EXP-009; it is not repaired here. Validation can use the seasonal estimate if recent PM history is absent, while inference raises when a test station has no eligible PM history. See the focused test in `tests/test_seasonal_history.py`.
