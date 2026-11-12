from .validation import validate_config
from .counts import panel_counts
from .fleiss import fleiss
from .bootstrap import row_bootstrap
from .fingerprint import fingerprint

def analyze_snapshot(snapshot):
 """只依据排队时刻冻结的资料批次计算，不读取数据库现状。"""
 study=snapshot['study'];specimens=snapshot['specimens'];votes=snapshot['votes'];config=snapshot['config']
 validate_config(config);rows=panel_counts(study,specimens,votes);matrix=[r['counts'] for r in rows];result=fleiss(matrix)
 for item,P in zip(rows,result['item_agreement']):item['agreement']=P
 bootstrap=row_bootstrap(matrix,config['bootstrap_repeats'],config['seed'])
 return {**result,'source_study':study,'categories':study['categories'],'raters':study['raters'],'items':rows,'bootstrap':bootstrap,'fingerprint':fingerprint(study,specimens,votes,config),'snapshot_version':snapshot.get('version'),'interpretation':'Agreement relative to empirical category marginals, not accuracy against a gold standard. Fixed complete three-person panel; bootstrap resamples whole iid specimens, not votes or new raters.'}
