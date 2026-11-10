# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import hashlib, json, numpy as np, pandas as pd
A='/mnt/user-data/attachments/67d9b4d0-a806-5af5-a403-5efe980aa0ec/'
R='/home/claude/acchasujal/aqi/reports/ml_pipeline/PRIVATE_WAR_ROOM/candidates/'
files={'ZFX65qUt B50':R+'warroom_Pfix_diur50_20261110.csv','vCB5vdBZ P_fix':A+'e9540ab2-task011_final_Pfix_20261110.csv','ckByeymY B25':A+'cd29a300-task011_final_Pfix_diur25_20261110.csv'}
exp={'ZFX65qUt B50':'b4d601812ec14c7f7516139e8f65085efcfe38b9e27c67469b5ed6774b798904','vCB5vdBZ P_fix':'f450b68212463f64bab67adfb0d98e1c4cce7ee83ec118f2564d38d738e34c13','ckByeymY B25':'96aff853c4692d29fd25c460e7efa0c25caa04fd84119c8bb0914ca0a1c6f2d1'}
tr=pd.read_csv(A+'d18f0f7d-Train_2.csv'); te=pd.read_csv(A+'c4e83537-Test.csv'); ss=pd.read_csv(A+'06f5f14a-SampleSubmission.csv')
print('Train sha',hashlib.sha256(open(A+'d18f0f7d-Train_2.csv','rb').read()).hexdigest()==('8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283'),'rows',len(tr))
tr['end']=pd.to_datetime(tr.timestamp_ist,utc=True); te['end']=pd.to_datetime(te.target_end_ist,utc=True)
m=te.merge(tr[['location_id','end','pm25']],on=['location_id','end'],how='left'); mm=m.pm25.notna().values
te['ts']=pd.to_datetime(te.target_start_ist,utc=True).dt.tz_convert('Asia/Kolkata')
priv=((te.ts>=pd.Timestamp('2026-11-11',tz='Asia/Kolkata'))&(te.ts<pd.Timestamp('2026-11-13',tz='Asia/Kolkata'))).values
P={}
for k,f in files.items():
    d=pd.read_csv(f); h=hashlib.sha256(open(f,'rb').read()).hexdigest(); P[k]=d.Target.values
    print(k,'sha ok',h==exp[k],'| cols',list(d.columns)==['ID','Target'],'rows',len(d),'order',(d.ID==ss.ID).all(),'finite',bool(np.isfinite(d.Target).all()),'nonneg',bool((d.Target>=0).all()),
          '| overlay exact',bool(np.allclose(d.Target[mm],m.pm25[mm])),'n',int(mm.sum()),'private overlay',int((mm&priv).sum()),'private rows',int(priv.sum()))
import os
for k,f in {'P_fix':A+'7b565635-task011_final_Pfix_20261110.manifest.txt','B25':A+'a8d32868-task011_final_Pfix_diur25_20261110.manifest.txt'}.items():
    j=json.load(open(f)); print(k,'manifest output_sha',j['output_sha256'][:12],'git',j['git_commit'][:8],'train',j['input_sha256']['Train.csv'][:12])
print('B50 manifest',json.load(open(R+'warroom_Pfix_diur50_20261110.csv.manifest.json'))['sha256'][:12])
b50,pf,b25=P['ZFX65qUt B50'][priv],P['vCB5vdBZ P_fix'][priv],P['ckByeymY B25'][priv]
rd=lambda a,b: round(float(np.sqrt(np.mean((a-b)**2))),2)
print('private-row prediction diversity: RMS diff B50-P_fix',rd(b50,pf),'B50-B25',rd(b50,b25),'P_fix-B25',rd(pf,b25),'| corr B50/P_fix',round(float(np.corrcoef(b50,pf)[0,1]),3),'B50/B25',round(float(np.corrcoef(b50,b25)[0,1]),3),'P_fix/B25',round(float(np.corrcoef(pf,b25)[0,1]),3))
print('private means B50/P_fix/B25',b50.mean().round(1),pf.mean().round(1),b25.mean().round(1))
