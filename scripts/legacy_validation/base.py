import sys; sys.path.insert(0,'.')
from common import *
tr,W=load()
S=list(W.columns)
CLEAN=W.where(W<1000)           # drop sensor-glitch spikes from history statistics
HC=CLEAN.clip(upper=300)        # winsorised history
def hist(C): return HC.loc[:C]
def preds(C,tgt,name):
    h=hist(C); out={}
    def lvl(n,f='mean'):
        x=h.iloc[-n:]; return getattr(x,f)()
    if name=='last': return pd.DataFrame({s:h[s].ffill().iloc[-1] for s in S},index=tgt)
    if name.startswith('mean') or name.startswith('med'):
        n=int(name[4 if name.startswith('mean') else 3:]); v=lvl(n,'mean' if name.startswith('mean') else 'median')
        return pd.DataFrame({s:[v[s]]*len(tgt) for s in S},index=tgt)
    if name.startswith('diur'):   # hour-of-day profile over last D days (mean), D from name
        D=int(name[4:]); x=h.iloc[-24*D:]; prof=x.groupby(x.index.hour).mean()
        return pd.DataFrame({s:prof[s].reindex(tgt.hour).values for s in S},index=tgt)
    if name.startswith('dmed'):
        D=int(name[4:]); x=h.iloc[-24*D:]; prof=x.groupby(x.index.hour).median()
        return pd.DataFrame({s:prof[s].reindex(tgt.hour).values for s in S},index=tgt)
    if name.startswith('pool'):   # pooled cross-station diurnal profile, scaled by station level
        D=int(name[4:]); x=h.iloc[-24*D:]; m=x.mean(axis=1); prof=m.groupby(m.index.hour).mean(); prof=prof/prof.mean()
        lv=x.mean()
        return pd.DataFrame({s:lv[s]*prof.reindex(tgt.hour).values for s in S},index=tgt)
    raise
def run(names,gap,start='2025-03-20',end='2026-10-30',step=1):
    rows=[]
    for C in pd.date_range(start,end,freq=f'{step}D'):
        C=C+pd.Timedelta(hours=23)           # last observed hour-ending stamp
        t0=C+pd.Timedelta(hours=gap); tgt=pd.date_range(t0+pd.Timedelta(hours=1),periods=48,freq='h')
        y=W.reindex(tgt)
        if y.notna().sum().sum()<100 or hist(C).iloc[-72:].notna().sum().min()<30: continue
        for n in names:
            p=preds(C,tgt,n)
            for s in S:
                m=y[s].notna()
                for t,yy,pp in zip(tgt[m],y[s][m],p[s][m]): rows.append((C,n,s,t,yy,pp))
    return pd.DataFrame(rows,columns=['C','model','st','t','y','p'])
def score(df,label=''):
    d=df.assign(e=df.p-df.y); d['e2']=d.e**2
    g=d.groupby('model')
    cl=d[d.y<500].groupby('model').e2.mean()**.5
    fold=d.groupby(['model','C']).e2.mean().pow(.5).groupby('model').agg(['median','std'])
    res=pd.DataFrame({'RMSE_raw':g.e2.mean()**.5,'RMSE_y<500':cl,'bias':g.e.mean(),'fold_med':fold['median'],'fold_sd':fold['std']})
    return res.sort_values('RMSE_y<500').round(2)
if __name__=='__main__':
    names=['last','mean24','mean72','mean168','med24','med72','med168','diur3','diur7','diur14','dmed7','pool3','pool7','pool14']
    for gap in (48,96):
        df=run(names,gap,step=2)
        df.to_pickle(f'base_gap{gap}.pkl')
        print('GAP',gap,'folds',df.C.nunique()); print(score(df))
        r=df[df.C>='2026-09-15']; print('--- since 2026-09-15 (post-monsoon, closest regime)'); print(score(r))
        r=df[(df.C>='2025-10-01')&(df.C<'2025-12-10')]; print('--- Oct-Dec 2025 (same season last year)'); print(score(r))
