from collections import Counter
import numpy as np
from .fleiss import fleiss,UndefinedKappa

def row_bootstrap(counts,repeats,seed):
 matrix=np.asarray(counts,dtype=int);N=len(matrix);rng=np.random.default_rng(seed);records=[];values=[];failures=Counter()
 for i in range(repeats):
  indices=rng.integers(0,N,size=N);sample=matrix[indices]
  try:
   result=fleiss(sample);value=result['kappa'];values.append(value);records.append({'repeat':i,'sample_indices':indices.tolist(),'kappa':value,'valid':True,'reason':None})
  except UndefinedKappa as error:
   reason=str(error);failures[reason]+=1;records.append({'repeat':i,'sample_indices':indices.tolist(),'kappa':None,'valid':False,'reason':reason})
 edges=np.linspace(-1,1,21);histogram={'edges':edges.tolist(),'counts':np.histogram(values,bins=edges)[0].tolist()}
 valid=len(values);eligible=valid*10>=repeats*9;interval=np.quantile(values,[.025,.975],method='linear').tolist() if eligible else None
 return {'seed':seed,'requested_repeats':repeats,'valid_repeats':valid,'invalid_repeats':repeats-valid,'valid_fraction':valid/repeats,'invalid_reasons':dict(failures),'interval':interval,'confidence_level':.95,'interval_status':'reported' if eligible else 'insufficient_valid','interval_reason':'有效比例≥90%，有效重复的2.5%/97.5%线性percentile经验区间' if eligible else '有效重复少于90%，不报告经验区间','quantile_method':'numpy.quantile(method=linear)','histogram':histogram,'replicates':records,'resampling_unit':'entire specimen count row with replacement; fixed same three raters','interpretation':'Percentile bootstrap conditional on the fixed rater panel and iid specimens. Excludes uncertainty from drawing new raters and is not classification accuracy.'}
