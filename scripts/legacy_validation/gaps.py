import sys; sys.path.insert(0,'.')
from base import *
names=['last','mean24','mean72','mean168','diur7','pool3']
for gap in (0,24,48,72,96,120):
    df=run(names,gap,start='2026-09-20',end='2026-10-30',step=2)
    s=score(df)
    print('gap',gap,'h  folds',df.C.nunique(),' ', {m:float(s.loc[m,'RMSE_y<500']) for m in names})
