# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import sys; sys.path.insert(0,'/home/claude/acchasujal/aqi/src')
from pathlib import Path
import pandas as pd, numpy as np
from mumbai_pm25.historical_archive import load_2024_history, P_FIX_SERIES
D=Path('/tmp/claude-0/-home-claude/67d9b4d0-a806-5af5-a403-5efe980aa0ec/scratchpad/data'); IST='Asia/Kolkata'
tr=pd.read_csv(D/'Train.csv'); tr['start']=pd.to_datetime(tr.timestamp_ist,utc=True).dt.tz_convert(IST)-pd.Timedelta(hours=1)
ar=load_2024_history(D/'AdditionalHistory.zip')
names={11606:'Borivali',11611:'Malad',3409510:'Byculla',3409511:'Shivaji'}
def series(year,st):
    if year==2024:
        g=ar[ar.series_id.isin(P_FIX_SERIES[st])]; return g.groupby('hour_start').pm25.mean()
    return tr[tr.location_id==st].set_index('start').pm25
T0={2024:'2024-10-31 18:00',2025:'2025-10-21 18:00'}
def preds(s,t0):
    cut=t0+pd.Timedelta(hours=39); s=s[s.index+pd.Timedelta(hours=1)<=cut]
    r72=s[s.index>cut-pd.Timedelta(hours=73)].dropna(); r168=s[s.index>cut-pd.Timedelta(hours=169)]
    base=s[(s.index>=t0-pd.Timedelta(days=10))&(s.index<t0-pd.Timedelta(days=3))].where(lambda x:x<1000).median()
    c=r168.where(r168<1000).clip(upper=300); prof=c.groupby(c.index.hour).mean()
    return dict(med72=r72.median(),med168=r168.median(),base=base,prof=prof)
res=[]
for yr in T0:
    for sh in (-1,0,1):
        t0=pd.Timestamp(T0[yr],tz=IST)+pd.Timedelta(days=sh)
        for st in names:
            s=series(yr,st)
            if s.empty or (yr==2024 and st==3409511): continue
            p=preds(s,t0); tg=pd.date_range(t0+pd.Timedelta(hours=54),periods=48,freq='h')
            y=s.reindex(tg)
            for h,yy in zip(tg,y):
                if np.isfinite(yy):
                    d7=p['prof'].get(h.hour,np.nan); d7=p['med72'] if not np.isfinite(d7) else d7
                    res.append(dict(year=yr,shift=sh,st=names[st],y=yy,med72=p['med72'],med168=p['med168'],base=p['base'],diur7=d7,
                                    m72_d50=.5*p['med72']+.5*d7,base_d50=.5*p['base']+.5*d7))
r=pd.DataFrame(res); cands=['med72','med168','base','diur7','m72_d50','base_d50']
rm=lambda g,c: float(np.sqrt(np.mean((g[c]-g.y)**2)))
print('Event-aligned RMSE (history-only candidates, no seasonal archive), geometry: cutoff t0+39h, targets t0+54..102h')
for (yr,sh),g in r.groupby(['year','shift']):
    print(yr,f'shift{sh:+d}','n',len(g),{c:round(rm(g,c),1) for c in cands},'mean y',round(g.y.mean(),1))
print('\npooled both events/shifts:',{c:round(rm(r,c),1) for c in cands})
print('\n2026 level comparison (per station): median72 / pre-event baseline [Oct29-Nov5) / 2026 private P_fix mean / B50 mean')
au=pd.read_csv('reports/ml_pipeline/task011/task011_final_row_audit.csv'); pv=au[au['private']]
cut=pd.Timestamp('2026-11-10 09:00',tz=IST); t0=pd.Timestamp('2026-11-08 18:00',tz=IST)
for st in names:
    s=tr[tr.location_id==st].set_index('start').pm25; p=preds(s,t0)
    g=pv[pv.location_id==st]; b50=np.where(g.diur7.notna(),.5*g.P_fix+.5*g.diur7,g.P_fix)
    print(names[st],round(p['med72'],1),round(p['base'],1),round(g.P_fix.mean(),1),round(float(b50.mean()),1),'| diur7 mean',round(g.diur7.mean(),1))
