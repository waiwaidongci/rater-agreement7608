from .fingerprint import fingerprint
SNAPSHOT_VERSION='queued-source-snapshot-v1'

def build_source_snapshot(study,specimens,votes,config):
 """冻结排队当时的研究声明、试样（含补注）、逐票与参数；后续编辑只影响新运行。"""
 return {
  'version':SNAPSHOT_VERSION,
  'study':dict(study),
  'specimens':[dict(s) for s in specimens],
  'votes':[dict(v) for v in votes],
  'config':dict(config),
 }

def snapshot_fingerprint(snapshot):
 return fingerprint(snapshot['study'],snapshot['specimens'],snapshot['votes'],snapshot['config'])

def snapshot_fingerprint_current(db,run):
 """对数据库当前资料按同一口径计算指纹；与排队指纹不同说明排队后发生过改票/补注。"""
 from .source import source_data
 study,items,votes=source_data(db,run.study_id)
 return fingerprint(study,items,votes,run.config)
