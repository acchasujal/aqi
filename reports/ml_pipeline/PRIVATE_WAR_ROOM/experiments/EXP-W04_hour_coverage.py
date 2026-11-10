# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import pandas as pd, numpy as np
A='/mnt/user-data/attachments/67d9b4d0-a806-5af5-a403-5efe980aa0ec/'
tr=pd.read_csv(A+'d18f0f7d-Train_2.csv')
e=pd.to_datetime(tr.timestamp_ist,utc=True).dt.tz_convert('Asia/Kolkata'); tr['start']=e-pd.Timedelta(hours=1)
cut=pd.Timestamp('2026-11-10 09:00',tz='Asia/Kolkata')
w=tr[(tr.start+pd.Timedelta(hours=1)<=cut)&(tr.start>cut-pd.Timedelta(hours=169))]
print('last-week counts by start hour (all stations):'); print(w.groupby(w.start.dt.hour).size().to_dict())
for st,g in w.groupby('location_id'): print(st, g.groupby(g.start.dt.hour).size().reindex(range(24),fill_value=0).tolist())
# overall frequency of each start hour per station in whole Train
tr['sh']=tr.start.dt.hour
print((tr.groupby('sh').size()/tr.groupby('sh').size().max()).round(2).to_dict())
# how often hour-gaps vs missing: per-month coverage of start hours 0 and 23
tr['m']=tr.start.dt.to_period('M')
print(tr[tr.sh.isin([23,0])].groupby(['m','sh']).size().unstack().to_string())
