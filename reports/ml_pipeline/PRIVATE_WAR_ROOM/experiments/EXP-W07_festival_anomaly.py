# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import sys; sys.path.insert(0,'/home/claude/acchasujal/aqi/src')
from pathlib import Path
import pandas as pd, numpy as np
from mumbai_pm25.historical_archive import load_2024_history, P_FIX_SERIES
D=Path('/tmp/claude-0/-home-claude/67d9b4d0-a806-5af5-a403-5efe980aa0ec/scratchpad/data')
IST='Asia/Kolkata'
tr=pd.read_csv(D/'Train.csv'); tr['start']=pd.to_datetime(tr.timestamp_ist,utc=True).dt.tz_convert(IST)-pd.Timedelta(hours=1)
ar=load_2024_history(D/'AdditionalHistory.zip')
names={11606:'Borivali',11611:'Malad',3409510:'Byculla',3409511:'ShivajiNagar'}
def series(year,st):
    if year==2024:
        g=ar[ar.series_id.isin(P_FIX_SERIES[st])]; return g.groupby('hour_start').pm25.mean()
    g=tr[tr.location_id==st]; return g.set_index('start').pm25
def clean(s): return s.where(s<1000)
T0={2024:'2024-10-31 18:00',2025:'2025-10-21 18:00',2026:'2026-11-08 18:00'}
WIN={'pre24':(-24,0),'night0-12':(0,12),'post0-24(12-36)':(12,36),'post24-48(36-60)':(36,60),'post48-72(60-84)':(60,84),'lastpre-cutoff(15-39)':(15,39),'target-analog(54-102)':(54,102)}
def table(shift_days=0):
    out=[]
    for yr,t in T0.items():
        t0=pd.Timestamp(t,tz=IST)+pd.Timedelta(days=shift_days)
        for st in names:
            s=clean(series(yr,st)); base=s[(s.index>=t0-pd.Timedelta(days=10))&(s.index<t0-pd.Timedelta(days=3))]
            b=base.median(); r={'year':yr,'station':names[st],'base_med':round(b,1),'base_n':int(base.notna().sum())}
            for k,(a,z) in WIN.items():
                w=s[(s.index>=t0+pd.Timedelta(hours=a))&(s.index<t0+pd.Timedelta(hours=z))].dropna()
                r[k]=round(w.median()/b,2) if len(w)>=max(3,(z-a)//4) else np.nan
                r[k+'_n']=len(w)
            out.append(r)
    return pd.DataFrame(out)
t=table(0)
pd.set_option('display.width',250)
print('RATIO of window median to pre-event baseline median (n hours in *_n)')
print(t[['year','station','base_med','base_n']+[k for k in WIN]].to_string(index=False))
print('\nhours available:'); print(t[['year','station']+[k+'_n' for k in WIN]].to_string(index=False))
for sh in (-1,1):
    print(f'\nSENSITIVITY t0 shifted {sh:+d} day: ratios');
    print(table(sh)[['year','station']+[k for k in WIN]].to_string(index=False))
# raw hourly peak and last-24h for 2026
print('\n2026 hourly medians across stations, Nov 7-10 (hour-start IST):')
s26=tr[(tr.start>=pd.Timestamp('2026-11-07',tz=IST))].pivot_table(index='start',columns='location_id',values='pm25')
s26.columns=[names[c] for c in s26.columns]
print(s26.resample('6h').median().round(0).to_string())
