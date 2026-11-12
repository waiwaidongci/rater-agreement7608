from fractions import Fraction
import numpy as np
class UndefinedKappa(ValueError):pass

def fleiss(counts):
 raw=np.asarray(counts)
 if raw.ndim!=2 or raw.shape[0]<2 or raw.shape[1]<2 or not np.isfinite(raw).all() or (raw<0).any() or not np.equal(raw,np.floor(raw)).all():raise ValueError('计数矩阵须至少2试样/2类的非负整数')
 matrix=raw.astype(np.int64);sizes=matrix.sum(axis=1);n=int(sizes[0]);N=len(matrix)
 if n!=3 or not np.all(sizes==n):raise ValueError('每行必须固定3票')
 pair_numerators=[sum(int(v)*(int(v)-1) for v in row) for row in matrix];P=[float(Fraction(v,n*(n-1))) for v in pair_numerators];pbar=Fraction(sum(pair_numerators),N*n*(n-1));totals=[int(v) for v in matrix.sum(axis=0)];den=(N*n)**2;pe=Fraction(sum(v*v for v in totals),den)
 if pe==1:raise UndefinedKappa('Pe=1：全部票落同一类别，κ未定义')
 kappa=(pbar-pe)/(1-pe)
 return {'kappa':float(kappa),'pbar':float(pbar),'pe':float(pe),'item_agreement':P,'category_totals':totals,'category_prevalence':[v/(N*n) for v in totals],'specimen_count':N,'raters_per_specimen':n,'total_votes':N*n}
