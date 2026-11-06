import sys; sys.path.insert(0,'.')
from common import *
pd.set_option('display.width',250)
tr,W=load()
for lab,a,b in [('Oct2026','2026-10-01','2026-11-03'),('Nov2025','2025-11-01','2025-12-01'),('Oct2025','2025-10-01','2025-11-01')]:
    x=W[a:b].where(W<1000); print(lab); print(x.describe(percentiles=[.5,.9,.99]).round(1).T)
# spike coincidence Nov 2025: hours where SHI>300 and what others were
x=W['2025-11-01':'2025-12-01']; s=x[x.SHI>300]; print('SHI>300 hours Nov25:',len(s)); print('others median at those hours:',s[['BOR','BYC','MAL']].median().round(0).to_dict())
# hour-of-day of spikes
print(s.index.hour.value_counts().sort_index().to_dict())
# Nov 2025 SHI vs others daily medians
d=W['2025-10-25':'2025-11-20'].where(W<1000).resample('D').median().round(0); print(d)
# 11-12 Nov 2025 values
print(W['2025-11-11':'2025-11-12'].where(W<1000).describe().round(1).T)
# cross-station correlation of hourly values recent
print(W['2026-09-15':].corr().round(2))
print('lag-1/24/48/72/96/168 autocorr (pooled, since Sep 15 2026):')
z=W['2026-09-15':].where(W<1000)
for L in (1,6,24,48,72,96,168): print(L, round(np.nanmean([z[c].corr(z[c].shift(L)) for c in z]),2))
