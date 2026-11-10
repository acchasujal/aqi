# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import sys, time
sys.path.insert(0,'/home/claude/acchasujal/aqi/src')
import pandas as pd, numpy as np
from zoneinfo import ZoneInfo
from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import ForecastBlock, labelled_blocks
from mumbai_pm25.historical_archive import load_2024_history
from pathlib import Path
IST=ZoneInfo('Asia/Kolkata'); D=Path('/tmp/claude-0/-home-claude/67d9b4d0-a806-5af5-a403-5efe980aa0ec/scratchpad/data')
train,test,sample,_=load_data(D); archive=load_2024_history(D/'AdditionalHistory.zip')
blocks=[ForecastBlock(t,t-pd.Timedelta(hours=15),t-pd.Timedelta(hours=15)) for t in pd.date_range("2025-04-02 00:00","2026-11-04 00:00",freq="7D",tz=IST)]
t0=time.time(); rows,cov=labelled_blocks(train,archive,blocks); print('built',time.time()-t0,'s',rows.shape)
rows.to_pickle(D/'oof_rebuilt.pkl')
old=pd.read_csv('/home/claude/acchasujal/aqi/reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz')
for c in ['fold_id','target_start']:
    old[c]=pd.to_datetime(old[c],utc=True); rows[c]=pd.to_datetime(rows[c],utc=True)
m=rows.merge(old,on=['location_id','fold_id','target_start'],suffixes=('','_old'),validate='one_to_one')
print('rows',len(rows),len(old),len(m))
for c in ['y','median24','median72','median168','diur7','P_fix','archive_target','archive_decay72']:
    a,b=m[c].astype(float),m[c+'_old'].astype(float)
    print(c,'max abs diff',np.nanmax(np.abs(a-b)),'nan mismatch',(a.isna()!=b.isna()).sum())
