import hashlib,json
VERSION='fixed-panel-fleiss-row-bootstrap-v1'
def fingerprint(study,specimens,votes,config):
 payload={'version':VERSION,'study':study,'specimens':sorted(specimens,key=lambda s:s['reference']),'votes':sorted(votes,key=lambda v:(v['specimen_id'],v['rater'])),'config':config}
 return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
