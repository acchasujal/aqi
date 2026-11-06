import sys,warnings; sys.path.insert(0,'.'); warnings.filterwarnings('ignore')
from common import *
import lightgbm as lgb
from sklearn.ensemble import ExtraTreesRegressor
tr,W=load(); S=list(W.columns)
HC=W.where(W<1000).clip(upper=300)
def build(gap,c0='2025-03-10',c1='2026-10-31'):
    rows=[]
    for Cd in pd.date_range(c0,c1,freq='D'):
        C=Cd+pd.Timedelta(hours=23); h=HC.loc[:C]
        if len(h)<24*8: continue
        x168=h.iloc[-168:]; x72=h.iloc[-72:]; x24=h.iloc[-24:]; x336=h.iloc[-336:]
        pooled={n:x.mean().mean() for n,x in (('p24',x24),('p72',x72),('p168',x168))}
        prof7=x168.groupby(x168.index.hour).mean()
        tgt=pd.date_range(C+pd.Timedelta(hours=gap+1),periods=48,freq='h')
        for si,s in enumerate(S):
            if x72[s].notna().sum()<24: continue
            m168=x168[s].mean()
            base=dict(C=C,st=s,si=si,m24=x24[s].mean(),m72=x72[s].mean(),m168=m168,m336=x336[s].mean(),
                      med72=x72[s].median(),sd168=x168[s].std(),last=h[s].ffill().iloc[-1],
                      p24=pooled['p24'],p72=pooled['p72'],p168=pooled['p168'],
                      lastday_mean=x24[s].mean(), pk168=x168[s].max())
            for k,t in enumerate(tgt):
                r=dict(base); r['t']=t; r['hz']=gap+k+1; r['hr']=t.hour; r['dow']=t.dayofweek; r['doy']=t.dayofyear
                r['prof7']=prof7[s].get(t.hour,np.nan); r['same_hr_yday']=h[s].iloc[-24+((t.hour-23-1)%24)] if False else np.nan
                rows.append(r)
    df=pd.DataFrame(rows)
    df['y']=W.stack().reindex(pd.MultiIndex.from_arrays([df.t,df.st])).values
    df['lvl']=df.m168
    return df
BASEF=['si','hr','dow','hz','m24','m72','m168','m336','med72','sd168','last','p24','p72','p168','prof7','pk168']
def fit_predict(trn,tst,kind):
    trn=trn[(trn.y.notna())&(trn.y<1000)&(trn.lvl>1)]
    f=BASEF+(['doy'] if 'doy' in kind else [])
    if kind.startswith('ratio'):
        ytr=np.log(trn.y.clip(lower=1)/trn.lvl); inv=lambda p,d: np.exp(p)*d.lvl.fillna(d.m72).values
    elif kind.startswith('sqrt'):
        ytr=np.sqrt(trn.y); inv=lambda p,d: np.clip(p,0,None)**2
    else:
        ytr=trn.y.clip(upper=300); inv=lambda p,d: p
    if 'et' in kind:
        m=ExtraTreesRegressor(120,min_samples_leaf=40,max_features=0.6,n_jobs=-1,random_state=0).fit(trn[f].fillna(-1),ytr)
        return inv(m.predict(tst[f].fillna(-1)),tst)
    m=lgb.LGBMRegressor(n_estimators=200,n_jobs=4,learning_rate=0.03,num_leaves=15,min_child_samples=150,subsample=0.8,subsample_freq=1,colsample_bytree=0.8,reg_lambda=5,random_state=0,verbose=-1)
    m.fit(trn[f],ytr); return inv(m.predict(tst[f]),tst)
def evaluate(df,gap,kinds,c0,c1,step=2):
    out=[]
    for Ce in pd.date_range(c0,c1,freq=f'{step}D'):
        Ce=Ce+pd.Timedelta(hours=23)
        trn=df[df.C<=Ce-pd.Timedelta(hours=gap+48)]
        tst=df[df.C==Ce]; tst=tst[tst.y.notna()]
        if len(tst)<50 or len(trn)<5000: continue
        d=tst[['C','st','t','y']].copy()
        d['diur7']=tst.prof7.values; d['mean168']=tst.m168.values; d['mean72']=tst.m72.values
        for k in kinds: d[k]=fit_predict(trn,tst,k)
        out.append(d)
    return pd.concat(out)
def report(res,models):
    r=res[res.y<500]
    rows=[]
    for m in models:
        e=r[m]-r.y; f=r.assign(e2=e**2).groupby('C').e2.mean()**.5
        byst=(r.assign(e2=e**2).groupby('st').e2.mean()**.5).round(1).to_dict()
        rows.append((m,round((e**2).mean()**.5,2),round(e.mean(),2),round(f.median(),2),round(f.std(),2),byst))
    return pd.DataFrame(rows,columns=['model','RMSE','bias','fold_med','fold_sd','by_station']).sort_values('RMSE')
if __name__=='__main__':
    kinds=['lgb','ratio','ratio_doy','sqrt']
    import os
    for gap in (48,96):
        df=pd.read_pickle(f'feat_gap{gap}.pkl') if os.path.exists(f'feat_gap{gap}.pkl') else build(gap)
        df.to_pickle(f'feat_gap{gap}.pkl')
        for lab,c0,c1 in (('RECENT 2026-09-20..10-30','2026-09-20','2026-10-30'),('SPRING-DECLINE 2026-02-20..04-30','2026-02-20','2026-04-30'),('SUMMER 2026-05-15..09-10','2026-05-15','2026-09-10')):
            res=evaluate(df,gap,kinds,c0,c1,step=3); res.to_pickle(f'res_gap{gap}_{lab[:6]}.pkl')
            sys.stdout.flush(); print('\n== gap',gap,lab,'folds',res.C.nunique()); print(report(res,['mean72','mean168','diur7']+kinds).to_string(index=False))
