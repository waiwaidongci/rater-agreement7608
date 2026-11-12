import json
from pathlib import Path
from celery import Celery
from sqlalchemy import select
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import AgreementRun
from src.services.analysis import analyze_snapshot
from src.services.audit import record
MISSING_SNAPSHOT='缺少排队时刻的原始资料快照（旧版运行），无法按原批计算；不会以当前资料补齐，请重新排队生成新运行。'
app=Celery('rater_agreement',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
def _claim_run(db,id):
 """行锁领取任务：终态（completed/failed）或已被其他worker领取（running）返回None，
 保证中断恢复与重复投递不会对同一运行新增/改写结果；queued 才领取并置 running。"""
 run=db.scalar(select(AgreementRun).where(AgreementRun.id==id).with_for_update())
 if not run or run.status!='queued':return None
 run.status='running';db.commit();return run
@app.task(name='rater.analyze',soft_time_limit=120,time_limit=150)
def analyze_run(id):
 with SessionLocal() as db:
  run=_claim_run(db,id)
  if run is None:return
  try:
   if not run.source_snapshot:
    raise ValueError(MISSING_SNAPSHOT)
   # 只按排队冻结的资料批次计算，绝不重新读取当前试样/逐票
   result=analyze_snapshot(run.source_snapshot)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'rater-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
   run.result=result;run.kappa=result['kappa'];run.pbar=result['pbar'];run.pe=result['pe'];run.status='completed';run.error=None;db.commit()
   record(db,'worker','run.completed',{'run_id':id,'fingerprint':result['fingerprint'],'valid_repeats':result['bootstrap']['valid_repeats']})
  except Exception as error:
   db.rollback();run=db.get(AgreementRun,id);run.status='failed';run.error=str(error)[:1000];db.commit()
   record(db,'worker','run.failed',{'run_id':id,'error':run.error})
