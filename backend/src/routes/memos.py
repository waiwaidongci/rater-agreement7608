from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers,admins
from src.models import ReviewMemo
from src.schemas.memo import MemoInput,ApprovalInput
from src.services.memos import create_memo,approve_memo
from src.controllers.export import export_memo
from src.utils.serialize import row
router=APIRouter()
@router.get('/memos')
def memos(db:Session=Depends(get_db),user=Depends(current_user)):return [row(m) for m in db.scalars(select(ReviewMemo).order_by(ReviewMemo.id.desc()))]
@router.post('/memos')
def create(data:MemoInput,db:Session=Depends(get_db),user=Depends(writers)):return create_memo(db,data,user.email)
@router.patch('/memos/{id}/approval')
def approve(id:int,data:ApprovalInput,db:Session=Depends(get_db),user=Depends(admins)):return approve_memo(db,id,data,user.email)
@router.get('/memos/{id}/export')
def export(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return export_memo(db,id,user.email)
