# Zindi Google Mumbai Data Challenge — Initial Plan (as of 6 Nov 2026)

Everything marked **[Measured]** was computed on your files in this session (code in `validation_code.zip`).
Tags: [Fact] [Strong Inference] [Weak Inference] [Speculation]. Confidence: High / Medium / Low.

## What I did NOT do (be aware)
- **Not inspected:** `Mumbai_Air_Quality_Starter.ipynb` (never opened), `Test.csv` beyond schema/dates, AdditionalHistory members beyond HistoryNotes + file listing.
- **Not tested:** any weather feature. My sandbox cannot reach Open-Meteo. `fetch_weather.py` is for you to run locally.
- **Not verified from primary sources:** Zindi rules (only your pasted pages), the 2020/2022 winners' code (the Zindi discussion pages were blocked; I rely on the summary in your pasted chat, which I could not confirm).
- Open-Meteo facts below come from Open-Meteo's own Historical Forecast docs and its Previous Runs post.

## 1. What the challenge really is  [Fact unless noted]
- Target: hourly PM2.5 at 4 stations, RMSE. 2,592 rows, but **only 11–12 Nov (192 rows, `scoring_block=private`) decides the prize.** All other rows are irrelevant to the final rank.
- Train: 47,849 rows, 2025‑02‑19 → 2026‑11‑02 23:00. No duplicates, `mean == pm25` exactly (redundant), `count` ∈ {3,4}.
- `available_at`: median lag **84 h** (min 39, max 382). Dictionary says it is not a verified publication time, so treat as indicative only.
- **Forecast gap [Strong Inference, Medium confidence]:** Final Train update is 10 Nov 09:00. With ~84 h lag, newest observation ≈ 6–8 Nov, so the private window starts **~2–4 days after your last known PM2.5**. Your history is stale for the whole scored period.
- **Public LB is the wrong yardstick.** 3–4 Nov starts ~1 day after Train ends; private starts 2–4+ days after. **[Measured]** naive RMSE rises with gap (Sep 20–Oct 30 folds): gap 0h ≈ 13–14, 24h ≈ 15, 48h ≈ 16–17, 72h ≈ 17, 96h ≈ 18–19, 120h ≈ 18–20. Expect private RMSE ≈ 15–19 for good history-only models, not 6.5.
- LB oddities [Fact]: rank 1 = 0, rank 2 = 2.3e‑15 (exact labels known). Ranks 3–10 cluster 6.5–7.1. Don't chase them; I can't tell how they got there.

## 2. Data audit findings [Measured]
- **Sensor glitches dominate raw RMSE.** Max 241,587 µg/m³ (Shivaji Nagar, 3 Dec 2025); Borivali 75,203 (Aug 2025); Byculla 3,320 (May 2026). Only 19 rows >1000, but they make whole‑history raw RMSE ≈ 1,465. Any model trained or evaluated naively on this is garbage. I excluded y≥1000 from training and winsorised history features at 300.
- **Shivaji Nagar spike regime, Oct–Dec 2025:** 40 hours >300 in Nov 2025 (daily clusters ~07–11h and 22–00h; the other 3 stations were ~66–78 at those hours). Oct 2026 max is 96. If it recurs on 11–12 Nov, no history‑based model can predict it. [Fact: pattern. Speculation: cause/recurrence.] On 11–12 Nov 2025 SHI had 466, 564, 688 readings.
- **Regime:** Oct 2026 medians ≈ 40–47 vs ≈ 13 in Sep; Nov–Dec 2025 medians ≈ 62 / 51. Last two weeks: ~35–40 and falling from the 16–18 Oct peak (~65–80). Previous-year Nov rise implies upward risk. [Measured regime; Weak Inference on direction.]
- Cross-station hourly correlation 0.70–0.83; pooled autocorrelation 0.97 (1h), 0.79 (24h), 0.67 (48h), 0.54 (96h), 0.51 (168h).
- Gaps: 24–26 Oct absent, 3–6 Nov excluded by design.
- Field safety: `pm25`=target; `mean` duplicate; `count`, `available_at`, `series_id`, `flag_high_1000`, `station_name`, `sensor_id`, `location_id` — **none usable as features** except station identity. `scoring_block`: do not use.
- AdditionalHistory: auxiliary stations end 16 Oct (per your own earlier audit), source IDs unmapped. [Strong Inference] negligible value for Nov forecasts. **Avoid.**

## 3. Validation design [Measured]
Rolling origin: cutoff = daily 23:00; predict 48 h starting `gap` hours later; train only on samples whose target window ended before the cutoff. Gaps 48 and 96 h (bracketing the expected private gap). Evaluation on y<500 (raw spikes unpredictable). Folds overlap (every 2–3 days), so effective independent folds are ~5–12 per regime. **Differences <~1 RMSE are inside noise (fold SD 6–8 in the autumn regime).**

### Baselines, gap 48h, 2026‑09‑15 → (RMSE y<500)
| model | RMSE | bias |
|---|---|---|
| diurnal profile, last 7 d | 15.00 | −7.2 |
| mean 168 h | 15.16 | −7.2 |
| mean 72 h | 15.89 | −4.7 |
| mean 24 h | 15.98 | −3.8 |
| last obs | 18.12 | +0.8 |
| 14‑day profile | 17.67 | −10.3 |
Calendar-only/ weather-only: not run.

### ML vs baseline (LightGBM, 200 trees; ratio = target is log(y / 7‑day station mean); `doy` adds day‑of‑year)
| regime / gap | diur7 | mean168 | lgb raw | sqrt | ratio | **ratio_doy** | **blend(ratio_doy, diur7)** |
|---|---|---|---|---|---|---|---|
| Autumn 2026, 48h (12 folds) | 15.13 | 15.27 | 16.00 | 17.18 | 17.29 | 15.27 | **14.43** |
| Autumn 2026, 96h (11) | 18.97 | 19.09 | 17.86 | 19.65 | 21.28 | 17.10 | **16.82** |
| Spring decline, 48h (24) | 18.79 | 18.41 | 18.74 | 17.78 | 17.66 | 17.05 | 17.20 |
| Spring decline, 96h (24) | 21.73 | 21.49 | 23.45 | 22.95 | 22.71 | 21.75 | **21.11** |
| Summer, 48h (37) | 7.42 | 7.37 | 7.25 | 7.02 | 7.11 | 7.00 | **6.92** |
| Summer, 96h (38) | 7.75 | 7.38 | 7.89 | — | — | 7.05 | 7.10 |
Per-station RMSE and bias are in the code output (Autumn 48h: MAL worst ≈ 17–18, BOR best ≈ 12–13).

**Reading:** ML gives at most ~1–2 RMSE over the 7-day mean, inconsistently. Plain `lgb` on raw y and sqrt/log targets lose to the baseline in the autumn regime (**[Measured]** — the "sqrt beats log" lesson did not transfer). Blend(ratio_doy, diur7) is best or within 0.05 of best in 5 of 6 cells and beats `diur7` in all 6. ExtraTrees, XGBoost, CatBoost, ARIMA, TFT, stacking: **not tested**, with no evidence they'd help.

Caveat on `doy`: one year of history only; it works as "what last Oct→Nov did". [Strong Inference] physically sensible (post-monsoon build-up), but a single-year seasonal prior is fragile. [Medium confidence]

## 4. External data
| Source | Verdict | Why |
|---|---|---|
| Open-Meteo Forecast API (7-day) | **Test first** | At issue time 10 Nov you know weather for 11–12 Nov at ~0.5–2.5 days lead; your PM history is 2–4+ days stale. This is the one thing that could break the staleness limit. |
| Open-Meteo Historical Forecast API | Use for *training* features, with caution | Docs: each run's early hours are stitched into one series, so it is ≈ analysis quality, not a multi‑day vintage; model versions change over time. Train/inference mismatch is real but small at ≤2.5 d lead. [Strong Inference] |
| Open-Meteo Previous Runs API | Probably not | Per the Open-Meteo post: stores ~3 months only, whole-day offsets; verify current limits. |
| ERA5 / ERA5-Land reanalysis | Avoid as a substitute | 5‑day publication delay; perfect-hindsight weather overstates skill. |
| IMD/METAR | Optional, low priority | Single airport point. Not examined. |
| Static layers (buildings, roads, landfill, population, pincode) | **Avoid** | No hourly variation; station identity already captures them with 4 stations. |
| Satellite/fire | Skip | No time to integrate; unverified. |
| Other-station history, 2018–2024 archives | Avoid | Unmapped IDs, different averaging conventions (per HistoryNotes). |
**Rules conflict (from your pasted pages):** Overview allows ClimateVerse catalogue datasets; Full Rules say "only datasets provided." Open-Meteo is in the ClimateVerse catalogue (Fact, from the pasted listing), so use is defensible but **get written organiser confirmation before the final upload.** Also unresolved: private score = latest valid submission vs best of 2 selected; 140 vs 300 submissions; 5 Nov window described as 1–2 Nov (Info page) vs 3–4 Nov (dictionary); public/private split 30/70 vs 20/80.

## 5. Final initial plan
**Model (build now, no weather):**
1. History features: station 24/72/168/336 h means (spikes dropped, winsorised at 300), 72 h median, 168 h std/max, last value, pooled 4‑station means, 7‑day same‑hour profile, hour, dow, horizon, station id (+ `doy`).
2. LightGBM on log(y/level7d), clip train y<1000, seeded.
3. Final prediction = 0.5 × LightGBM(ratio_doy) + 0.5 × 7‑day diurnal profile. Predict every one of the 2,592 rows with the same cutoff logic; only private rows matter.
4. Retrain on the 10 Nov 09:00 data, submit, and **leave that as the latest valid submission.**
**Weather track (in parallel):** run `fetch_weather.py` locally, send me `weather_hist.csv` + `weather_fcst.csv`; I'll test the identical pipeline with/without wind u/v, BLH, humidity, rain, temperature. Keep weather only if it beats no-weather in ≥ 2 of 3 regimes at both gaps.
**Do not:** random K‑fold, deep nets, stacking, tune on the public LB, spend submissions on small variants.
**Submissions:** ≤10/day. Use 2–3 for checks (format, public sanity vs baseline), save the rest. Final upload 10 Nov, well before 23:59 IST.
**Submission checklist:** 2,592 rows, ID order identical to Test.csv, column `Target`, all finite and ≥0, no NaN, `sample - submission` ID set equal, rerun script reproduces the file (fixed seeds).

## 6. Ranked next experiments
1. Weather features vs no-weather (needs your CSVs). Potential: largest; Low-Medium confidence.
2. Re-check blend weight and ratio_doy on folds after 10 Nov data arrives (e.g. 0.3–0.7).
3. Shivaji Nagar spike hedge (small upward bias) — evaluate on Oct–Dec 2025 only; likely reject. [Speculation]
4. ExtraTrees/XGBoost on same features as diversity for the blend.
5. Per-station vs shared model.

## 7. Scoring this approach as a competition entry
Novelty 3/10 · Execution difficulty 3/10 · Technical feasibility 9/10 · Business/impact 4/10 · Judge appeal 3/10 · Defensibility 2/10. **Probability of finishing top 3 on private: ~10–15% [Low confidence]** — this is mostly a lottery on the weather and on spikes during 11–12 Nov. Probability of ending in the better half: ~65% [Weak Inference].

WHY THIS WINS: robust, leakage-safe, validated at the right horizon; avoids the public‑LB trap.
WHY THIS FAILS: a Shivaji Nagar spike or a regime shift on 11–12 Nov; no weather = no information about the actual conditions; seasonal prior based on 1 year.
BIGGEST RISK: spikes/glitch values in the 192 private rows (a single 600 reading at one station adds ~ +6 RMSE overall: sqrt(600²/192)=43 on that fraction; i.e. one hour can dominate).
BIGGEST ADVANTAGE: most competitors are probably tuned to a 1‑day horizon on the public window.
HIGHEST-LEVERAGE IMPROVEMENT: forecast weather for 11–12 Nov.

## 8. Critical review
- **Assumption that could invalidate everything:** the 2–4‑day gap. If the 10 Nov update contains data through 9–10 Nov, short-gap models (blending in `last`) win (gap 0 RMSE ≈ 13 vs 17).
- **Leakage risk:** weather "historical forecast" values are better than what live forecasts deliver; and my `doy` feature leans on last year.
- **Unrealistic fold:** Spring and summer regimes aren't the target regime; only the Sep 20–Oct 30 folds resemble it, and they overlap.
- **Overfit risk:** the blend weight (0.5) and the LightGBM hyperparameters are untuned and single-seed.
- **Overlooked:** Diwali/festival effect on 8–12 Nov is not modelled (was in Oct 2025 for SHI spikes) — Diwali 2026 date not checked. [Speculation that it matters.]
- **Cheapest high-value experiment:** weather vs no-weather on the same folds.

VERDICT: Ship the blend now, add weather only if it wins across regimes.
KEY INSIGHT: The task is a 2–4‑day-ahead problem, not the 1‑day problem the public LB measures.
MOST LIKELY MISTAKE: Over-reading a 1–2 RMSE difference from ~10 overlapping folds, and trusting public LB.
BIGGEST RISK: Spike/glitch hours in the private window.
BEST ALTERNATIVE: `diur7` baseline (no ML), within ~1 RMSE of everything else.
NEXT BEST ACTION: Run `fetch_weather.py` locally and send me the two CSVs.
CONFIDENCE: Medium on the diagnosis and validation numbers; Low on the final rank.
