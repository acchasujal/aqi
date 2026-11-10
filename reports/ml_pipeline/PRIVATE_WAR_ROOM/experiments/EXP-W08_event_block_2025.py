# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import sys; sys.path.insert(0,'/home/claude/acchasujal/aqi/src')
from pathlib import Path
import pandas as pd, numpy as np
from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import ForecastBlock, labelled_blocks
from mumbai_pm25.historical_archive import load_2024_history
D=Path('/tmp/claude-0/-home-claude/67d9b4d0-a806-5af5-a403-5efe980aa0ec/scratchpad/data'); IST='Asia/Kolkata'
train,test,sample,_=load_data(D); archive=load_2024_history(D/'AdditionalHistory.zip')
t0=pd.Timestamp('2025-10-21 18:00',tz=IST)
blocks=[ForecastBlock(t0+pd.Timedelta(days=s,hours=54), t0+pd.Timedelta(days=s,hours=39), t0+pd.Timedelta(days=s,hours=39)) for s in (-1,0,1)]
rows,cov=labelled_blocks(train,archive,blocks)
print(cov.to_string(index=False))
rows['diur7f']=rows.diur7.fillna(rows.P_fix)
for w in (25,50): rows[f'B{w}']=(1-w/100)*rows.P_fix+w/100*rows.diur7f
v=rows[rows.y.notna()]
for fid,g in v.groupby('fold_id'):
    print('\nblock target_start',fid, 'rows',len(g),'diur7 coverage',g.diur7.notna().mean().round(2))
    print({c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in ['median72','median168','archive_target','P_fix','B25','B50','diur7f']},
          'bias',{c:round(float((g[c]-g.y).mean()),1) for c in ['P_fix','B25','B50','diur7f']}, 'mean y',round(g.y.mean(),1))
    print(' per station RMSE P_fix/B25/B50:',{int(s):tuple(round(float(np.sqrt(np.mean((h[c]-h.y)**2))),1) for c in ['P_fix','B25','B50']) for s,h in g.groupby('location_id')})
