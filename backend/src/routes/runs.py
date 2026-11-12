from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import AgreementRun
from src.schemas.run import RunInput
from src.services.runs import create_run,requeue_run,batch_status,MISSING_SNAPSHOT
from src.utils.serialize import row
router=APIRouter()
def _with_batch(db,r):
 data=row(r);data['batch']=batch_status(db,r)
 if r.status=='completed' and not r.source_snapshot:
  data['error']=(data['error']+' ' if data['error'] else '')+MISSING_SNAPSHOT
 return data
@router.get('/runs')
def runs(db:Session=Depends(get_db),user=Depends(current_user)):return [_with_batch(db,r) for r in db.scalars(select(AgreementRun).order_by(AgreementRun.id.desc()))]
@router.get('/runs/{id}')
def one(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 run=db.get(AgreementRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 return _with_batch(db,run)
@router.post('/runs')
def create(data:RunInput,db:Session=Depends(get_db),user=Depends(writers)):return create_run(db,data,user.email)
@router.post('/runs/{id}/requeue')
def requeue(id:int,db:Session=Depends(get_db),user=Depends(writers)):return requeue_run(db,id,user.email)
