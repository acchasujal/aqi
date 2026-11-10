# FINAL RECOMMENDATION (revised after W06-W10; owner performs all Zindi actions)
SELECT: ZFX65qUt = warroom_Pfix_diur50_20261110.csv  sha256 b4d601812ec14c7f7516139e8f65085efcfe38b9e27c67469b5ed6774b798904
SELECT: vCB5vdBZ = task011_final_Pfix_20261110.csv   sha256 f450b68212463f64bab67adfb0d98e1c4cce7ee83ec118f2564d38d738e34c13
Do not select: ckByeymY = task011_final_Pfix_diur25 (sha 96aff853...a2d1) - uploaded, still valid.
Why this changed from B50+B25: only the better of the 2 selected counts, so the pair should be diverse. B50 is best on 83-origin clean-regime evidence (y<1000 24.43 vs P_fix 25.25) and on 2024-type events; P_fix is the best of the three on 2025-type post-festival blocks (40.8-45.3 vs B50 45.6-54.4). Pair B50+P_fix: OOF E[min per-origin RMSE] 16.136 vs 16.175 for B50+B25; full-target 302.52 vs 302.56; 2025 event blocks mean 42.6 vs 46.5. Margins on OOF are tiny; the event evidence is n=1. Confidence: medium-low in the pair choice, no cost to adopt.
Full-target RMSE remains a tie among all (extremes = 2 Shivaji fault episodes). If a >=1000 fault reading hits the private window the ranking is luck.
No dynamic or festival candidate qualified; none created. Conflict note: the instruction default was B50+B25 if nothing qualified; this deviates on evidence stated above.

## Final lock (after Stage 3 independent pair analysis)
Pair: ZFX65qUt (warroom_Pfix_diur50_20261110.csv, B50) + vCB5vdBZ (task011_final_Pfix_20261110.csv, P_fix). Do not select ckByeymY unless owner prefers B25 as partner.
Evidence: complete-block min RMSE (all raw labels) B50+P_fix 302.519 vs B50+B25 302.560 vs P_fix+B25 302.845; B50+P_fix vs B50+B25 is a tie (17/17/49). Decision margin is small; chosen for diversity and the n=1 2025 event block. Either B50-containing pair is defensible; P_fix+B25 is not.
Steps: tick ZFX65qUt and vCB5vdBZ only; click save; refresh the page; confirm exactly those two are checked; upload nothing afterwards. Uploaded != selected != saved.
