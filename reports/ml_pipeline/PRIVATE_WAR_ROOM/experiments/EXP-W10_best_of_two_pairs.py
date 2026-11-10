# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import sys; sys.path.insert(0,'/home/claude/acchasujal/aqi/src')
import pandas as pd, numpy as np
from pathlib import Path
from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import ForecastBlock, labelled_blocks
from mumbai_pm25.historical_archive import load_2024_history
o=pd.read_csv('reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz'); v=o[o.y.notna()].copy()
v['d']=v.diur7.fillna(v.P_fix)
for w in (25,50): v[f'B{w}']=(1-w/100)*v.P_fix+w/100*v.d
def orig_rmse(df,c,mask):
    g=df[mask]; return g.groupby('fold_id').apply(lambda x: np.sqrt(np.mean((x[c]-x.y)**2)))
m=v.y<1000
R={c:orig_rmse(v,c,m) for c in ['P_fix','B25','B50']}
print('OOF (83 origins, y<1000): mean per-origin RMSE',{c:round(float(r.mean()),3) for c,r in R.items()})
for a,b in [('B50','B25'),('B50','P_fix'),('B25','P_fix')]:
    mn=np.minimum(R[a],R[b]); print(f'  pair {a}+{b}: mean of per-origin min RMSE',round(float(mn.mean()),3),' median',round(float(mn.median()),3))
# full-target per-origin (incl. extremes)
R2={c:orig_rmse(v,c,v.y>-1) for c in ['P_fix','B25','B50']}
for a,b in [('B50','B25'),('B50','P_fix')]:
    mn=np.minimum(R2[a],R2[b]); print(f'  FULL-target pair {a}+{b}: mean min',round(float(mn.mean()),2),'| origins where pair-min differs by >1% from other pair: n/a')
# event blocks 2025 (3 shifts), reuse labelled_blocks
D=Path('/tmp/claude-0/-home-claude/67d9b4d0-a806-5af5-a403-5efe980aa0ec/scratchpad/data'); IST='Asia/Kolkata'
train,test,sample,_=load_data(D); archive=load_2024_history(D/'AdditionalHistory.zip')
t0=pd.Timestamp('2025-10-21 18:00',tz=IST)
blocks=[ForecastBlock(t0+pd.Timedelta(days=s,hours=54),t0+pd.Timedelta(days=s,hours=39),t0+pd.Timedelta(days=s,hours=39)) for s in (-1,0,1)]
rows,_=labelled_blocks(train,archive,blocks); e=rows[rows.y.notna()].copy(); e['d']=e.diur7.fillna(e.P_fix)
for w in (25,50): e[f'B{w}']=(1-w/100)*e.P_fix+w/100*e.d
E={c:e.groupby('fold_id').apply(lambda x: np.sqrt(np.mean((x[c]-x.y)**2))) for c in ['P_fix','B25','B50']}
print('\n2025 event blocks RMSE:',{c:E[c].round(1).tolist() for c in E})
for a,b in [('B50','B25'),('B50','P_fix')]: print(f'  pair {a}+{b} min per block',np.minimum(E[a],E[b]).round(1).tolist(),'mean',round(float(np.minimum(E[a],E[b]).mean()),2))
