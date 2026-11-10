# WAR ROOM STATE (2026-11-10, IST clock unavailable from tool; session started ~16:00 IST; deadline 23:59:59 IST)
Repo: acchasujal/aqi main afd28272dc221e3ab3d170b0661c7732a552e03b (manifests cite 00f766aa; only diff = TASK011 script+tests). Clone is read-only; nothing pushed. Local files in reports/ml_pipeline/PRIVATE_WAR_ROOM/.
Data (all hashes verified vs manifests): Train 8adbcf55...a283 (48,400 rows), Test cdb2b6c3..., Sample 5806d610..., Stations 383269fa..., AdditionalHistory 3233061c...
Submitted controls: P_fix f450b682...4c13; B25 96aff853...a2d1. Both verified: 2592 ordered IDs, finite, 1284 exact overlay (657 public+627 unscored, 0 private), 192 private rows 15-62h lead.
Zindi mapping CONFIRMED by screenshots: ZFX65qUt=B50 (public 5.96e-15), vCB5vdBZ=P_fix, ckByeymY=B25 (all public ~0 because overlay). 18/200 used. None selected yet in screenshots. Rules say choose 2; Info text says latest valid submission - CONFLICT, select 2 explicitly.
Results (y<1000 RMSE / full): med168 25.88/2391.50; P_fix 25.25/2391.72; B25 24.69/2391.74; B50 24.43/2391.76; B100 24.81/2391.82.
Rejected: NNLS stack S1. Unresolved: Shivaji archive-fallback inconsistency, friend-branch models, weather.
New candidate: candidates/warroom_Pfix_diur50_20261110.csv sha b4d60181...8904
Next: 1) owner decides Slot A/B and selects 2 on Zindi before deadline; 2) optional: fix OOF-reuse provenance guard; 3) optional: test w=0.6 / hour-23,0 handling (low value).

## Update after W06-W10
Dynamic/lead blends REJECTED; festival-robust baseline REJECTED (2024 vs 2025 opposite). 2026 still elevated at cutoff (Malad 245 on 10-Nov 00-06). Event-aligned 2025: P_fix<B25<B50 RMSE (n=1).
CURRENT RECOMMENDATION: select ZFX65qUt (B50) + vCB5vdBZ (P_fix). Next 3 actions: 1) owner selects those 2 on Zindi and saves; 2) optional OOF-reuse provenance guard; 3) optional: test Malad/Shivaji event downside (low evidence).

## Update after final audit
Remote main = deeecafcdd8c75d949d29c729d21093415bc0da5 (war-room docs/scripts only; candidate CSV deliberately not in git). Local backup tag backup/prepush-6ba0aba. Integrity of all 3 submissions verified. Pair lock: ZFX65qUt + vCB5vdBZ (tie-break decision, see FINAL_PRIVATE_RANKING_RECOMMENDATION.md). Owner still must select+save+refresh on Zindi.

## TASK012 update — 2026-11-10

TASK012 completed as research only on local main at 58fd180 (same as local origin/main ref). Full OOF rebuilt: 16,128 rows, 12,731 labels, 83 labelled origins; final 23 origins/3,545 labelled rows were forward evaluation. P_fix remains primary and B50 the hedge: full OOF RMSE 2391.716290/2391.761889; forward RMSE 11.1934/10.4333. Station alpha/shrinkage does not improve the forward primary control; residual challengers are rejected. Weather/spatial remain blocked. No submitted CSV or raw challenge file changed. Detailed artifacts are under reports/ml_pipeline/task012_vayudrishti_transfer/.

Correction after final TASK012 run: dimensionless alpha lambda=1 was selected on development; shrunk station calibration RMSE10.8791 and unregularized station alpha10.6894, both behind B50 10.4333. Both beat P_fix11.1934 on the 23-origin forward slice, which has no target >=500. Neither alpha candidate is promoted. B50 paired delta vs P_fix is -0.7601 (4-origin moving-block95% interval -1.1878 to -0.2621;18/23 wins). The final report supersedes earlier provisional alpha notes.
