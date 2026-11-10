# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import pandas as pd, numpy as np
rng=np.random.default_rng(20261110)
o=pd.read_csv('reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz')
v=o[o.y.notna()].copy()
v['diur7f']=v.diur7.fillna(v.P_fix)
for w in (0,10,25,50,75,100): v[f'B{w}']=(1-w/100)*v.P_fix+w/100*v.diur7f
v['Pfix_ge']=v.P_fix
y=v.y.values
print('extreme rows y>=1000:'); print(v[v.y>=1000][['location_id','target_start','y','P_fix','median168','last_pm','age_hours']].to_string())
print('y quantiles',np.quantile(y,[.5,.9,.99,.999]).round(1), 'n>=250',(y>=250).sum(),'n>=500',(y>=500).sum())
masks={'full':np.ones(len(v),bool),'y<1000':y<1000,'y<250':y<250}
cands=['median24','median72','median168','P_fix','B10','B25','B50','B75','B100','archive_decay72','archive_constant50']
print('\nRMSE by mask')
rows=[]
for c in cands:
    r={'model':c}
    for k,m in masks.items(): r[k]=np.sqrt(np.mean((v[c].values[m]-y[m])**2))
    r['MAE_<1000']=np.mean(np.abs(v[c].values[masks['y<1000']]-y[masks['y<1000']]))
    r['bias_<1000']=np.mean((v[c].values-y)[masks['y<1000']])
    rows.append(r)
print(pd.DataFrame(rows).round(3).to_string(index=False))
# paired block bootstrap over origins on y<1000 (and y<250), resample origins with replacement
folds=v.fold_id.values; uf=np.unique(folds)
def sse_by_fold(c,m):
    e=(v[c].values-y)**2*m
    s=pd.Series(e).groupby(folds).sum(); n=pd.Series(m.astype(int)).groupby(folds).sum()
    return s.reindex(uf).values,n.reindex(uf).values
def boot(a,b,mname,B=4000):
    m=masks[mname]; sa,n=sse_by_fold(a,m); sb,_=sse_by_fold(b,m)
    d=[]
    for _ in range(B):
        ix=rng.integers(0,len(uf),len(uf));
        d.append(np.sqrt(sa[ix].sum()/n[ix].sum())-np.sqrt(sb[ix].sum()/n[ix].sum()))
    d=np.array(d); return np.percentile(d,[2.5,50,97.5]).round(3), (d<0).mean().round(3)
print('\nPaired origin-block bootstrap: RMSE(A)-RMSE(B), negative => A better')
for a,b in [('B25','P_fix'),('B10','P_fix'),('B50','P_fix'),('median168','P_fix'),('P_fix','median72'),('B25','median168'),('B50','B25')]:
    for mn in ('y<1000','y<250','full'):
        print(a,'vs',b,mn,*boot(a,b,mn))
# per origin win-rate on y<1000
m=masks['y<1000']
def fold_rmse(c):
    s,n=sse_by_fold(c,m); return np.sqrt(s/np.maximum(n,1))
fr={c:fold_rmse(c) for c in ['P_fix','B25','B50','median168','diur7f']}
ok=np.array([n>0 for n in sse_by_fold('P_fix',m)[1]])
print('\norigins with labels',ok.sum(),'B25 beats P_fix in',(fr['B25'][ok]<fr['P_fix'][ok]).sum(),'origins; B50 beats',(fr['B50'][ok]<fr['P_fix'][ok]).sum(),'; med168 beats',(fr['median168'][ok]<fr['P_fix'][ok]).sum())
# leave out top-5 worst origins by P_fix SSE
print('origin SSE share top5 (y<1000):',(pd.Series(sse_by_fold('P_fix',m)[0]).nlargest(5).sum()/sse_by_fold('P_fix',m)[0].sum()).round(3))
# per station
print('\nper station RMSE y<1000')
for st,g in v[m].groupby('location_id'):
    print(st,len(g),{c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in ['median72','median168','P_fix','B25','B50','B100']})
# per lead bucket
v['lb']=pd.cut(v.forecast_lead_hours,[0,24,36,48,70])
print('\nper lead bucket y<1000');
for lb,g in v[m].groupby('lb',observed=True): print(lb,len(g),{c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in ['median168','P_fix','B25','B50']})
print('lead range',v.forecast_lead_hours.min(),v.forecast_lead_hours.max())
# last 8 origins (most recent regime: Sep-Nov 2026)
last=uf[-9:]; mm=v.fold_id.isin(last).values&m
print('\nrecent 9 origins y<1000 n',mm.sum(),{c:round(float(np.sqrt(np.mean((v[c].values[mm]-y[mm])**2))),2) for c in ['median168','P_fix','B25','B50','B100']})
