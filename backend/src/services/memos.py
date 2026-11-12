from sqlalchemy import select
from fastapi import HTTPException
from src.models import AgreementRun,ReviewMemo
from src.utils.serialize import row
from .runs import batch_status,MISSING_SNAPSHOT
from .audit import record

def create_memo(db,data,actor):
 run=db.get(AgreementRun,data.run_id)
 if not run or run.status!='completed':raise HTTPException(422,'仅成功运行可建立口径复核说明')
 if not run.source_snapshot or not run.result or not run.queued_fingerprint:
  raise HTTPException(422,MISSING_SNAPSHOT)
 if db.scalar(select(ReviewMemo).where(ReviewMemo.name==data.name)):raise HTTPException(409,'说明名已存在')
 batch=batch_status(db,run)
 memo=ReviewMemo(**data.model_dump(),result_snapshot=run.result,created_by=actor)
 # 说明上留痕资料批次，便于复核时核对该说明引用的是哪一批逐票/参数
 memo.result_snapshot=dict(run.result);memo.result_snapshot['batch']={'snapshot_version':batch['snapshot_version'],'queued_fingerprint':batch['queued_fingerprint'],'current_fingerprint_at_memo':batch['current_fingerprint'],'current_matches_queued_at_memo':batch['current_matches_queued']}
 db.add(memo);db.commit();record(db,actor,'memo.created',{'memo_id':memo.id,'run_id':run.id,'fingerprint':run.queued_fingerprint});return row(memo)

def approve_memo(db,id,data,actor):
 memo=db.scalar(select(ReviewMemo).where(ReviewMemo.id==id).with_for_update())
 if not memo:raise HTTPException(404,'说明不存在')
 if memo.status!='draft':raise HTTPException(409,'说明已审阅，不可重复审批')
 memo.status=data.status;memo.review_note=data.review_note;db.commit();record(db,actor,'memo.reviewed',{'memo_id':id,'status':memo.status});return row(memo)
