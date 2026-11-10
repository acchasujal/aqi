# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import pandas as pd, numpy as np
A='/mnt/user-data/attachments/67d9b4d0-a806-5af5-a403-5efe980aa0ec/'
tr=pd.read_csv(A+'d18f0f7d-Train_2.csv'); te=pd.read_csv(A+'c4e83537-Test.csv'); ss=pd.read_csv(A+'06f5f14a-SampleSubmission.csv')
p1=pd.read_csv(A+'23c4459b-task011_final_Pfix_20261110.csv'); p2=pd.read_csv(A+'4b350258-task011_final_Pfix_diur25_20261110.csv')
print('rows',len(tr),len(te),len(p1),len(p2))
print('id order', (p1.ID==ss.ID).all(), (p2.ID==ss.ID).all(), (te.ID==ss.ID).all())
print('finite/nonneg', np.isfinite(p1.Target).all(), (p1.Target>=0).all(), np.isfinite(p2.Target).all(), (p2.Target>=0).all())
tr['end']=pd.to_datetime(tr.timestamp_ist,utc=True); te['end']=pd.to_datetime(te.target_end_ist,utc=True)
print('dup keys',tr.duplicated(['location_id','end']).sum())
m=te.merge(tr[['location_id','end','pm25']],on=['location_id','end'],how='left')
print('overlap rows',m.pm25.notna().sum()); print(m.groupby('scoring_block').pm25.apply(lambda s:s.notna().sum()))
te['ts']=pd.to_datetime(te.target_start_ist,utc=True).dt.tz_convert('Asia/Kolkata')
priv=(te.ts>=pd.Timestamp('2026-11-11',tz='Asia/Kolkata'))&(te.ts<pd.Timestamp('2026-11-13',tz='Asia/Kolkata'))
print('private rows',priv.sum(),'private matched',m.pm25.notna()[priv.values].sum())
print('scoring_block private rows',(te.scoring_block=='private').sum(), 'agree', (priv==(te.scoring_block=='private')).all())
mm=m.pm25.notna().values
print('overlay exact p1',np.allclose(p1.Target[mm],m.pm25[mm]),'p2',np.allclose(p2.Target[mm],m.pm25[mm]))
print('non-overlay differ p1/p2', (np.abs(p1.Target-p2.Target)[~mm]>1e-9).sum(), 'overlay differ',(np.abs(p1.Target-p2.Target)[mm]>1e-9).sum())
te['p1']=p1.Target; te['p2']=p2.Target
pv=te[priv.values]
print(pv.groupby('location_id')[['p1','p2']].describe().T.round(1).to_string())
print('corr',np.corrcoef(pv.p1,pv.p2)[0,1],'rmsdiff',np.sqrt(((pv.p1-pv.p2)**2).mean()))
# train extremes + last days
print(tr.pm25.describe()); print(tr.nlargest(10,'pm25')[['timestamp_ist','location_id','pm25','count','flag_high_1000']])
print(tr.groupby('location_id').end.agg(['min','max','count']))
