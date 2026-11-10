# ruff: noqa  (exploratory war-room script; kept verbatim as run)
import numpy as np, pandas as pd
rng=np.random.default_rng(20261110)
o=pd.read_csv('/home/claude/acchasujal/aqi/reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz')
v=o[o.y.notna()].copy(); d=v.diur7.fillna(v.P_fix)
for w in (25,50): v[f'B{w}']=(1-w/100)*v.P_fix+w/100*d
C=['P_fix','B25','B50']; uf=np.sort(v.fold_id.unique())
print('labelled origins',len(uf),'rows',len(v),'identical rows for all candidates (no NaN):',bool(v[C].notna().all().all()))
def blockrmse(df):
    return pd.DataFrame({c:df.groupby('fold_id').apply(lambda x: np.sqrt(np.mean((x[c]-x.y)**2))) for c in C}).loc[uf]
ext_orig=sorted(v[v.y>=1000].fold_id.unique()); print('origins containing y>=1000:',[str(x)[:10] for x in ext_orig])
pairs={'B50+P_fix':('B50','P_fix'),'B50+B25':('B50','B25'),'P_fix+B25':('P_fix','B25')}
def pairscore(R): return pd.DataFrame({k:np.minimum(R[a],R[b]) for k,(a,b) in pairs.items()})
def summarize(label,R,idx=None):
    S=pairscore(R);
    if idx is not None: S=S.loc[idx]; Rr=R.loc[idx]
    else: Rr=R
    print(f'\n[{label}] origins={len(S)}  mean / median pair-min block RMSE'); print(pd.DataFrame({'mean':S.mean(),'median':S.median()}).round(3).to_string())
    print('  single-candidate mean block RMSE:',Rr.mean().round(3).to_dict())
    for a,b in [('B50+P_fix','B50+B25'),('B50+P_fix','P_fix+B25'),('B50+B25','P_fix+B25')]:
        diff=(S[a]-S[b]); wins=int((diff<-1e-9).sum()); loss=int((diff>1e-9).sum()); ties=len(diff)-wins-loss
        print(f'  {a} vs {b}: mean diff {diff.mean():+.3f}; {a} better in {wins}, worse in {loss}, tied {ties}')
    return S
def mbb_ci(S,a,b,block=4,B=5000):
    x=(S[a]-S[b]).values; n=len(x); r=[]
    for _ in range(B):
        starts=rng.integers(0,n,int(np.ceil(n/block))); idx=np.concatenate([(s+np.arange(block))%n for s in starts])[:n]; r.append(x[idx].mean())
    return np.percentile(r,[2.5,97.5]).round(3)
# OFFICIAL-STYLE: all raw labels incl extremes
R=blockrmse(v); S=summarize('ALL RAW LABELS (official-style)',R)
for a,b in [('B50+P_fix','B50+B25'),('B50+P_fix','P_fix+B25')]: print(f'  moving-block bootstrap CI (len4) mean[{a}-{b}]:',mbb_ci(S,a,b))
Sf=summarize('ALL RAW LABELS, last 23 origins',R,idx=uf[-23:])
# excluding the two fault origins entirely (NON-OFFICIAL diagnostic)
keep=[x for x in uf if x not in ext_orig]
summarize('NON-OFFICIAL: excluding the fault-episode origins',R,idx=keep)
# y<1000 labels only (NON-OFFICIAL)
R2=blockrmse(v[v.y<1000]); S2=summarize('NON-OFFICIAL y<1000 rows, all origins',R2)
for a,b in [('B50+P_fix','B50+B25'),('B50+P_fix','P_fix+B25')]: print(f'  moving-block bootstrap CI mean[{a}-{b}]:',mbb_ci(S2,a,b))
summarize('NON-OFFICIAL y<1000, last 23 origins',R2,idx=uf[-23:])
print('\nper-origin single-candidate wins (y<1000 blocks): B50<P_fix',int((R2.B50<R2.P_fix).sum()),'; B25<P_fix',int((R2.B25<R2.P_fix).sum()),'; B50<B25',int((R2.B50<R2.B25).sum()))
print('share of origins where P_fix is best of three:',round(float((R2.P_fix<=R2[['B25','B50']].min(axis=1)).mean()),3))
# how often is P_fix better than B50 by >1 RMSE point (hedge value)
dd=R2.P_fix-R2.B50; print('origins where P_fix beats B50 by >0.5 RMSE:',int((dd<-0.5).sum()),'; B50 beats P_fix by >0.5:',int((dd>0.5).sum()))
print('2025 event blocks (W08, n=1 event, 3 shifts): block RMSE P_fix [40.8,45.3,41.7], B25 [42.8,48.9,47.8], B50 [45.6,53.3,54.4]; pair means B50+P_fix 42.6 vs B50+B25 46.5')
