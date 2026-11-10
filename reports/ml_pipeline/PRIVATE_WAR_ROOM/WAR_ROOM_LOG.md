# WAR ROOM LOG (append-only; IST clock unavailable, ordered entries)
1. Cloned main (afd2827); verified 8 data/CSV hashes vs manifests (sha256sum). Source hashes of run_task011/prepare/forecast/historical_archive equal manifest. Decision: controls reproducible.
2. EXP-W00 submission audit: IDs/order OK, overlay exact 1284, 0 private matches, scoring_block private==Nov 11-12 mask. Decision: integrity PASS.
3. Read run_task011.py: OOF cache reuse unguarded (L170-174). Read forecast.py/final_gap.py: features use only rows ended<=cutoff; inference shares predict_station_baseline; no leakage found.
4. EXP-W01 (pre-registered H1,H2): extremes = 2 Shivaji fault episodes; diur7 blend wins on y<1000, tie on full.
5. EXP-W02: S1 stack rejected; forward split supports B50.
6. EXP-W03: rebuilt OOF with current main, matches cache ~1e-14 (77s).
7. Built candidate B50 with asserts reproducing both submitted CSVs to 1e-9; sha b4d60181...8904. Decision: recommend B50 + B25 pending owner.
8. Zindi screenshots establish mapping: ZFX65qUt=warroom_Pfix_diur50 (public 5.96e-15), vCB5vdBZ=task011_final_Pfix, ckByeymY=task011_final_Pfix_diur25. New attachments e9540ab2/cd29a300 hash-equal to submitted P_fix/B25. 18/200 submissions; none selected yet in screenshots.
9. EXP-W06 (gate pre-registered): no dynamic blend beats B50 (y<1000 +0.10..+0.21, CI incl 0; 30-32/83 origins). Best diur weight ~60% on both days. REJECTED.
10. EXP-W07: festival anomalies by elapsed time. 2026 still elevated at cutoff (ratio 1.15 Borivali, 1.8-2.0 others); Malad hourly 245 on 10-Nov 00-06. 2025 post window collapsed to 0.13-0.41x baseline; 2024 archive stayed 1.0-1.4x (alignment uncertain; Shivaji absent).
11. EXP-W08: event-aligned 2025 blocks: P_fix < B25 < B50 RMSE in all 3 shifts (n=1 event).
12. EXP-W09: 2024 vs 2025 opposite (diur7 best 2024, worst 2025). Festival-robust baseline candidate REJECTED by pre-registered gate.
13. EXP-W10: pair analysis -> B50+P_fix marginally better than B50+B25 on OOF E[min], clearly better on 2025 event. Recommendation REVISED (new evidence: best-of-two geometry + event blocks): B50 + P_fix. No new candidate file created.
