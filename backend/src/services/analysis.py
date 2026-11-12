from .validation import validate_config
from .counts import panel_counts
from .fleiss import fleiss
from .bootstrap import row_bootstrap
from .fingerprint import fingerprint

def analyze(study,specimens,votes,config):
 validate_config(config);rows=panel_counts(study,specimens,votes);matrix=[r['counts'] for r in rows];result=fleiss(matrix)
 for row,P in zip(rows,result['item_agreement']):row['agreement']=P
 bootstrap=row_bootstrap(matrix,config['bootstrap_repeats'],config['seed'])
 return {**result,'source_study':study,'categories':study['categories'],'raters':study['raters'],'items':rows,'bootstrap':bootstrap,'fingerprint':fingerprint(study,specimens,votes,config),'interpretation':'Agreement relative to empirical category marginals, not accuracy against a gold standard. Fixed complete three-person panel; bootstrap resamples whole iid specimens, not votes or new raters.'}
