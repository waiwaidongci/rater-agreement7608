from sqlalchemy import select
from fastapi import HTTPException
from src.models import AgreementRun
from src.utils.serialize import row
from .source import source_data
from .snapshot import build_source_snapshot,snapshot_fingerprint,snapshot_fingerprint_current
from .validation import validate_source,validate_config
from .audit import record
MISSING_SNAPSHOT='缺少排队时刻的原始资料快照（旧版运行），无法按原批计算；不会以当前资料补齐，请重新排队生成新运行。'

def batch_status(db,run):
 """供结果页/复核说明核对资料批次：是否有冻结快照、排队指纹、与当前资料是否仍一致。"""
 info={'snapshot_version':run.source_snapshot.get('version') if run.source_snapshot else None,
       'queued_fingerprint':run.queued_fingerprint,
       'has_snapshot':bool(run.source_snapshot),
       'missing_snapshot':not bool(run.source_snapshot),
       'current_matches_queued':None,'current_fingerprint':None}
 if run.source_snapshot:
  current=snapshot_fingerprint_current(db,run);info['current_fingerprint']=current
  info['current_matches_queued']=(current==run.queued_fingerprint)
 return info

def create_run(db,data,actor):
 study,items,votes=source_data(db,data.study_id);config=data.model_dump(exclude={'study_id','name'})
 try:validate_source(study,items,votes);validate_config(config)
 except ValueError as error:raise HTTPException(422,str(error))
 if db.scalar(select(AgreementRun).where(AgreementRun.name==data.name)):raise HTTPException(409,'运行名已存在')
 # 排队当时即冻结试样、逐票与参数；worker执行时只按该批次计算，后续改票/补注只影响新运行
 snapshot=build_source_snapshot(study,items,votes,config)
 run=AgreementRun(study_id=data.study_id,name=data.name,config=config,source_snapshot=snapshot,queued_fingerprint=snapshot_fingerprint(snapshot),created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建任务';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id,'fingerprint':run.queued_fingerprint});return row(run)

def requeue_run(db,id,actor):
 """中断恢复：对未到终态（queued 消息丢失或 running 进程中断）的同一任务重新入队，
 不新建运行、不新增结果，仍按原批快照计算；终态任务拒绝重投，靠行锁领取保证重复投递幂等。"""
 run=db.get(AgreementRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 if run.status not in ('queued','running'):raise HTTPException(409,'仅未到终态（queued/running）的任务可恢复重投，完成/失败任务不会重复执行')
 if not run.source_snapshot:raise HTTPException(422,MISSING_SNAPSHOT)
 if run.status=='running':run.status='queued'
 db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建任务';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.requeued',{'run_id':id,'fingerprint':run.queued_fingerprint});return row(run)
