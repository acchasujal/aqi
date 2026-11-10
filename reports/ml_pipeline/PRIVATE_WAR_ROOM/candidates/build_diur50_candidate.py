# ruff: noqa  (exploratory war-room script; kept verbatim as run)
"""WAR-ROOM experimental: build 0.5*P_fix + 0.5*diur7 from the frozen row audit.
Never overwrites; verifies the identical formula at w=0.25 reproduces the submitted CSV exactly."""
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[4]
AUD=ROOT/'reports/ml_pipeline/task011/task011_final_row_audit.csv'
SUB=Path(sys.argv[1]); SUB25=Path(sys.argv[2]); OUT=Path(__file__).parent
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=pd.read_csv(AUD); pf=pd.read_csv(SUB); b25=pd.read_csv(SUB25)
assert list(a.ID)==list(pf.ID)==list(b25.ID)
m=a.released_observation_match.to_numpy(bool)
def blend(w):
    v=np.where(np.isfinite(a.diur7),(1-w)*a.P_fix+w*a.diur7,a.P_fix)
    return np.where(m,a.overlay_pm25,v)
assert np.abs(blend(0.0)-pf.Target).max()<1e-9, 'P_fix mismatch'
assert np.abs(blend(0.25)-b25.Target).max()<1e-9, 'B25 mismatch'
t=blend(0.5); assert np.isfinite(t).all() and (t>=0).all()
name='warroom_Pfix_diur50_20261110.csv'; out=OUT/name
assert not out.exists(), 'refuse to overwrite'
pd.DataFrame({'ID':a.ID,'Target':t}).to_csv(out,index=False)
priv=a.private.to_numpy(bool)
man={'file':name,'sha256':sha(out),'formula':'0.5*P_fix+0.5*diur7 (diur7 NaN -> P_fix); exact released-label overlay (1284 rows)',
 'rows':len(t),'overlay_rows':int(m.sum()),'private_overlay_rows':int((m&priv).sum()),
 'reproduced_controls':{'P_fix_sha256':sha(SUB),'Pfix_diur25_sha256':sha(SUB25)},
 'audit_input_sha256':sha(AUD),'builder_sha256':sha(__file__),'git_base':'afd28272dc221e3ab3d170b0661c7732a552e03b',
 'zindi_action':'NOT uploaded; owner decision'}
(OUT/(name+'.manifest.json')).write_text(json.dumps(man,indent=2)+'\n'); print(json.dumps(man,indent=2))
pv=pd.DataFrame({'st':a.location_id[priv],'p1':pf.Target[priv],'p25':b25.Target[priv],'p50':t[priv]})
print(pv.groupby('st').mean().round(1)); print('corr p25-p50',np.corrcoef(pv.p25,pv.p50)[0,1].round(4),'rms diff',np.sqrt(((pv.p25-pv.p50)**2).mean()).round(2))
