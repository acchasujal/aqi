from pathlib import Path
import os
import pandas as pd, numpy as np
DATA_DIR = Path(os.environ.get('ZINDI_DATA_DIR', Path(__file__).resolve().parent)).expanduser().resolve()
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
tr=pd.read_csv(DATA_DIR/'Train.csv')
tr['ts']=pd.to_datetime(tr.timestamp_ist,format='mixed',utc=True).dt.tz_convert('Asia/Kolkata')
tr['av']=pd.to_datetime(tr.available_at,format='ISO8601',utc=True).dt.tz_convert('Asia/Kolkata')
tr['lag_h']=(tr.av-tr.ts).dt.total_seconds()/3600
print(tr.lag_h.describe()); print(tr.groupby(tr.av.dt.date).size().tail(15))
print(tr.groupby('station_name').pm25.describe(percentiles=[.5,.99]))
print(tr[tr.pm25>300].sort_values('ts')[['ts','station_name','pm25','count']].to_string())
print(tr.groupby(tr.ts.dt.to_period('M')).pm25.agg(['size','median','mean']))
# recent daily medians per station
r=tr[tr.ts>='2026-10-10'].copy(); r['d']=r.ts.dt.date
print(r.pivot_table(index='d',columns='station_name',values='pm25',aggfunc='median').round(1))
print(r.pivot_table(index='d',columns='station_name',values='pm25',aggfunc='size'))
