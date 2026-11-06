ZINDI MUMBAI VALIDATION SCRIPTS — PORTABLE COPY

This is a portable copy of the six validation scripts supplied by Claude.
Only the data path was changed; modelling logic is otherwise unchanged.

1) Put Train.csv in this folder, OR set ZINDI_DATA_DIR to the folder containing Train.csv.
2) Install dependencies:
   python -m pip install numpy pandas scikit-learn lightgbm
3) Run baseline / gap experiment:
   python base.py
   python gaps.py
4) Run ML comparisons (can take longer):
   python ml.py
5) Inspect spike patterns:
   python spikes.py
6) Audit available_at and recent distributions:
   python audit2.py

IMPORTANT LIMITATIONS
- This package does not include Test.csv and does not build a final submission.
- The published metrics in Claude's plan use y < 500 for the diagnostic RMSE; that is NOT the official full-target RMSE.
- The feature/validation logic and spike handling still require the review described in our analysis.
- LightGBM may not have a native Windows ARM64 wheel on a Snapdragon X laptop. If installation fails, use Colab for ml.py; the simpler base.py and gaps.py do not require LightGBM.
- Do not use the original weather_hist.csv from the Historical Forecast API as a 2–4 day-ahead weather vintage. Use archived individual runs / Previous Runs for a fair backtest.
