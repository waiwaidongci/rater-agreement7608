from sqlalchemy import select
from fastapi import HTTPException
from src.models import AgreementStudy,Specimen,RaterVote
from src.utils.serialize import row
from .validation import validate_source
from .audit import record

def create_study(db,data,actor):
 if db.scalar(select(AgreementStudy).where(AgreementStudy.name==data.name)):raise HTTPException(409,'研究名已存在')
 source=data.model_dump(exclude={'specimens'});items=[{'id':i+1,'reference':s.reference,'description':s.description} for i,s in enumerate(data.specimens)];votes=[dict(v.model_dump(),specimen_id=i+1) for i,s in enumerate(data.specimens) for v in s.votes]
 try:validate_source(source,items,votes)
 except ValueError as error:raise HTTPException(422,str(error))
 study=AgreementStudy(**source);db.add(study);db.flush()
 for s in data.specimens:
  item=Specimen(study_id=study.id,reference=s.reference,description=s.description);db.add(item);db.flush()
  for v in s.votes:db.add(RaterVote(specimen_id=item.id,**v.model_dump()))
 db.commit();record(db,actor,'study.imported',{'study_id':study.id,'specimens':len(items)});return row(study)

def source_data(db,id):
 study=db.get(AgreementStudy,id)
 if not study:raise HTTPException(404,'研究不存在')
 items=list(db.scalars(select(Specimen).where(Specimen.study_id==id).order_by(Specimen.reference)));ids=[s.id for s in items];votes=list(db.scalars(select(RaterVote).where(RaterVote.specimen_id.in_(ids)).order_by(RaterVote.specimen_id,RaterVote.rater)))
 return row(study),[row(s) for s in items],[row(v) for v in votes]

def edit_vote(db,id,data,actor):
 vote=db.get(RaterVote,id)
 if not vote:raise HTTPException(404,'票不存在')
 item=db.get(Specimen,vote.specimen_id);study=db.get(AgreementStudy,item.study_id)
 if data.category not in study.categories:raise HTTPException(422,'类别不在预先声明列表')
 old=vote.category;vote.category=data.category;db.commit();record(db,actor,'vote.revised',{'vote_id':id,'old':old,'new':vote.category});return row(vote)

def edit_item(db,id,data,actor):
 item=db.get(Specimen,id)
 if not item:raise HTTPException(404,'试样不存在')
 item.description=data.description;db.commit();record(db,actor,'specimen.annotated',{'specimen_id':id});return row(item)
