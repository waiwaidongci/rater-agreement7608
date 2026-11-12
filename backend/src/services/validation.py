def validate_source(study,specimens,votes):
 categories=study['categories'];raters=study['raters']
 if not 2<=len(categories)<=6 or len(set(categories))!=len(categories) or any(not isinstance(c,str) or not c.strip() or len(c)>80 for c in categories):raise ValueError('类别须2..6个唯一非空声明，顺序固定')
 if len(raters)!=3 or len(set(raters))!=3 or any(not isinstance(r,str) or not r.strip() or len(r)>80 for r in raters):raise ValueError('须声明3位唯一固定标记者')
 if not 2<=len(specimens)<=240 or len({s['id'] for s in specimens})!=len(specimens) or len({s['reference'] for s in specimens})!=len(specimens):raise ValueError('须2..240个唯一试样')
 lookup={s['id']:[] for s in specimens}
 for v in votes:
  if v['specimen_id'] not in lookup or v['category'] not in categories or v['rater'] not in raters:raise ValueError('未知试样/类别/标记者')
  lookup[v['specimen_id']].append(v['rater'])
 for names in lookup.values():
  if len(names)!=3 or len(set(names))!=3 or set(names)!=set(raters):raise ValueError('每试样须同一固定3人面板各一票，不可缺票/重复')

def validate_config(config):
 b=config['bootstrap_repeats'];seed=config['seed']
 if type(b) is not int or not 400<=b<=1000 or type(seed) is not int or not 0<=seed<=1000000000 or config.get('panel_scope')!='fixed_three_raters':raise ValueError('B须400..1000，seed合法且固定三人面板')
