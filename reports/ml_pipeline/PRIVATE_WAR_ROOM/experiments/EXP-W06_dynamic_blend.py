# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import pandas as pd, numpy as np
rng=np.random.default_rng(20261110)
o=pd.read_csv('/home/claude/acchasujal/aqi/reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz')
v=o[o.y.notna()].copy().reset_index(drop=True)
d=v.diur7.fillna(v.P_fix); y=v.y.values; F=v.fold_id.values; uf=np.unique(F)
day=v.target_day.values; lead=v.forecast_lead_hours.values
def mk(w): return (1-w)*v.P_fix.values+w*d.values
W={'P_fix':np.zeros(len(v)),'B25':np.full(len(v),.25),'B50':np.full(len(v),.5),
 'DynA_50_25':np.where(day==1,.5,.25),'DynB_40_20':np.where(day==1,.4,.2),
 'Lin50to25':.5-.25*(lead-15)/47}
for k,w in W.items(): v[k]=mk(w)
print('days',np.unique(day),'lead',lead.min(),lead.max(),'rows',len(v),'origins',len(uf))
m_lt=y<1000; masks={'full':np.ones(len(v),bool),'y<1000':m_lt}
rm=lambda c,m: np.sqrt(np.mean((v[c].values[m]-y[m])**2))
rows=[]
for c in W: rows.append({'model':c,'full':rm(c,masks['full']),'y<1000':rm(c,m_lt),'MAE<1000':np.mean(np.abs(v[c].values[m_lt]-y[m_lt])),'bias<1000':np.mean((v[c].values-y)[m_lt])})
print(pd.DataFrame(rows).round(3).to_string(index=False))
def fs(c,m): return pd.Series((v[c].values-y)**2*m).groupby(F).sum().reindex(uf).values
n=lambda m: pd.Series(m.astype(int)).groupby(F).sum().reindex(uf).values
def boot(a,b,m,B=4000):
    sa,sb,nn=fs(a,m),fs(b,m),n(m); r=[]
    for _ in range(B):
        ix=rng.integers(0,len(uf),len(uf)); r.append(np.sqrt(sa[ix].sum()/nn[ix].sum())-np.sqrt(sb[ix].sum()/nn[ix].sum()))
    return np.percentile(r,[2.5,97.5]).round(3), round(float(np.sqrt(sa.sum()/nn.sum())-np.sqrt(sb.sum()/nn.sum())),3)
print('\nPaired block bootstrap, diff RMSE(A)-RMSE(B) [CI95], point')
for a in ['DynA_50_25','DynB_40_20','Lin50to25','B25']:
    for b in ['B50','P_fix'] if a!='B25' else ['P_fix']:
        for mn,m in masks.items():
            ci,pt=boot(a,b,m); print(f'{a} vs {b} {mn}: {pt} {ci}')
ok=n(m_lt)>0
for a in ['DynA_50_25','DynB_40_20','Lin50to25']:
    print(a,'beats B50 in origins (y<1000):',int((fs(a,m_lt)[ok]/n(m_lt)[ok]<fs('B50',m_lt)[ok]/n(m_lt)[ok]).sum()),'of',int(ok.sum()),'; beats P_fix:',int((fs(a,m_lt)[ok]<fs('P_fix',m_lt)[ok]).sum()))
last=np.sort(uf)[60:]; fm=np.isin(F,last)
print('\nforward last-23 origins rows',(fm&m_lt).sum(),'(full-target incl extremes? extremes in origins before) ')
for mn,m in [('y<1000',m_lt&fm),('full',fm)]:
    print(mn,{c:round(float(rm(c,m)),3) for c in W})
print('\nper station y<1000');
for st,g in v[m_lt].groupby('location_id'): print(st,{c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in W})
v['day']=day; print('\nper target day y<1000')
for dd,g in v[m_lt].groupby('day'): print('day',dd,len(g),{c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in W})
print('\nper lead bucket y<1000')
v['lb']=pd.cut(lead,[14,26,38,50,62])
for lb,g in v[m_lt].groupby('lb',observed=True): print(lb,len(g),{c:round(float(np.sqrt(np.mean((g[c]-g.y)**2))),2) for c in W})
# day-specific optimal diur weight (diagnostic)
for dd in (1,2):
    mm=m_lt&(day==dd); print('day',dd,'best w',min(range(0,101,10),key=lambda w: rm_w(w,mm)) if False else '', {w:round(float(np.sqrt(np.mean((((1-w/100)*v.P_fix+w/100*d).values[mm]-y[mm])**2))),3) for w in range(0,101,20)})
