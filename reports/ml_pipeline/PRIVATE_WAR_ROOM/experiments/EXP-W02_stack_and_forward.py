# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import pandas as pd, numpy as np
from scipy.optimize import nnls
rng=np.random.default_rng(7)
o=pd.read_csv('reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz')
v=o[o.y.notna()].copy().reset_index(drop=True)
v['diur7f']=v.diur7.fillna(v.P_fix)
v['lastc']=v.last_pm.clip(upper=300)
v['arch']=v.archive_target.fillna(v.median72)
y=v.y.values; m=y<1000
print('archive_target NaN share',v.archive_target.isna().mean().round(3),'by station',v.groupby('location_id').archive_target.apply(lambda s:s.isna().mean()).round(3).to_dict())
for B in ['B25','B50']: v[B]=(1-int(B[1:])/100)*v.P_fix+int(B[1:])/100*v.diur7f
# archive missing vs present at Shivaji
for st in (3409511,):
    g=v[(v.location_id==st)&m]
    miss=g.archive_target.isna()
    print('Shivaji RMSE y<1000 archive-missing rows',miss.sum(),{c:round(float(np.sqrt(np.mean((g.loc[miss,c]-g.loc[miss,'y'])**2))),1) for c in ['median72','P_fix','B50']},
          '| present rows',(~miss).sum(),{c:round(float(np.sqrt(np.mean((g.loc[~miss,c]-g.loc[~miss,'y'])**2))),1) for c in ['median72','P_fix','B50']})
X=['P_fix','diur7f','median24','median168','lastc','arch']
F=v.fold_id.values; uf=np.unique(F)
pred=np.full(len(v),np.nan)
for f in uf:
    tr=(F!=f)&m; te=F==f
    w,_=nnls(v.loc[tr,X].values,y[tr]); pred[te]=v.loc[te,X].values@w
wall,_=nnls(v.loc[m,X].values,y[m]); print('full-fit NNLS weights',dict(zip(X,wall.round(3))),'sum',wall.sum().round(3))
v['S1']=pred
def rm(c,mask): return np.sqrt(np.mean((v[c].values[mask]-y[mask])**2))
print('LOO-origin RMSE y<1000: S1',rm('S1',m).round(3),'B50',rm('B50',m).round(3),'B25',rm('B25',m).round(3),'P_fix',rm('P_fix',m).round(3))
# bootstrap S1 vs B50
def fs(c):
    e=(v[c].values-y)**2*m; return pd.Series(e).groupby(F).sum().reindex(uf).values
n=pd.Series(m.astype(int)).groupby(F).sum().reindex(uf).values
a,b=fs('S1'),fs('B50'); d=[]
for _ in range(4000):
    ix=rng.integers(0,len(uf),len(uf)); d.append(np.sqrt(a[ix].sum()/n[ix].sum())-np.sqrt(b[ix].sum()/n[ix].sum()))
print('S1-B50 CI',np.percentile(d,[2.5,50,97.5]).round(3))
ok=n>0; print('S1 beats B50 in',(a[ok]/n[ok]<b[ok]/n[ok]).sum(),'of',ok.sum(),'origins')
# time-forward check: fit on first 60 origins, test last 23 origins (more honest chronology)
order=np.sort(uf); tr_f=order[:60]; te_f=order[60:]
trm=np.isin(F,tr_f)&m; tem=np.isin(F,te_f)&m
w,_=nnls(v.loc[trm,X].values,y[trm]); v['S1f']=v[X].values@w
print('forward split: weights',dict(zip(X,w.round(3))),'test n',tem.sum(),{c:round(float(rm(c,tem)),3) for c in ['S1f','B50','B25','P_fix','median168']})
# forward-split test of plain diur weight: best w chosen on first 60 origins
ws=np.arange(0,101,5); r=[np.sqrt(np.mean((((1-w_/100)*v.P_fix+w_/100*v.diur7f).values[trm]-y[trm])**2)) for w_ in ws]
print('best diur weight on first 60 origins:',ws[int(np.argmin(r))]);
tw=ws[int(np.argmin(r))]; print('then on last 23 origins: chosen',round(float(rm('B50',tem)),3) if tw==50 else '', 'P_fix',round(float(rm('P_fix',tem)),3),'B25',round(float(rm('B25',tem)),3),'B50',round(float(rm('B50',tem)),3))
# curve of weight over all origins
print({w_:round(float(np.sqrt(np.mean((((1-w_/100)*v.P_fix+w_/100*v.diur7f).values-y)[m]**2))),3) for w_ in range(0,101,10)})
