from .validation import validate_source

def panel_counts(study,specimens,votes):
 validate_source(study,specimens,votes);ordered=sorted(specimens,key=lambda s:s['reference']);categories=study['categories'];lookup={s['id']:{} for s in ordered}
 for vote in votes:lookup[vote['specimen_id']][vote['rater']]=vote['category']
 rows=[]
 for specimen in ordered:
  labels=lookup[specimen['id']];counts=[sum(labels[r]==c for r in study['raters']) for c in categories];rows.append({'id':specimen['id'],'reference':specimen['reference'],'description':specimen['description'],'counts':counts,'votes':[{'rater':r,'category':labels[r]} for r in study['raters']]})
 return rows
