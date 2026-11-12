from sqlalchemy import select
from fastapi import HTTPException
from src.models import AgreementRun
from src.utils.serialize import row
from .source import source_data
from .validation import validate_source,validate_config
from .audit import record

def create_run(db,data,actor):
 study,items,votes=source_data(db,data.study_id);config=data.model_dump(exclude={'study_id','name'})
 try:validate_source(study,items,votes);validate_config(config)
 except ValueError as error:raise HTTPException(422,str(error))
 if db.scalar(select(AgreementRun).where(AgreementRun.name==data.name)):raise HTTPException(409,'运行名已存在')
 run=AgreementRun(study_id=data.study_id,name=data.name,config=config,created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建任务';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id});return row(run)
