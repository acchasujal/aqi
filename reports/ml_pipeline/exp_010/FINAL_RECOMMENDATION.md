# EXP-010 final recommendation

**RETAIN BASELINE — W50.** No challenger CSV was generated. W0, the provisional development RMSE winner, improves confirmation RMSE but fails the robustness criterion: its pooled development gain is entirely driven by the 2025-12-03 extreme window, counted in both 96h and 120h gap comparisons; non-extreme rows favor W50 and Malad/Byculla regress. W25 improves confirmation further but was not selected on development and cannot be promoted retrospectively. W50 remains the current production model and default CLI configuration. No leaderboard probing, Zindi upload, push, or merge occurred.

Historical station-series provenance, archive interval semantics, and leap-year matching remain unresolved as documented in EXP-008. EXP-010 did not change them. Full-target RMSE includes all labels. The confirmation period lacks extreme targets and November rows, limiting confidence in final private-regime transfer.
