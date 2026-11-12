import json
import numpy as np
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import User,AgreementStudy,Specimen,RaterVote,AgreementRun,ReviewMemo
from src.utils.security import hash_password
from src.utils.serialize import row
from src.services.analysis import analyze_snapshot
from src.services.snapshot import build_source_snapshot,snapshot_fingerprint

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','纪岚 · 图谱研究负责人'),('analyst','秦砚 · 标记分析员'),('viewer','陶野 · 口径观察员')]:
   if not db.scalar(select(User).where(User.email==f'{role}@shanxu.demo')):db.add(User(email=f'{role}@shanxu.demo',name=name,role=role,password_hash=hash_password('Shanxu2026!')))
  db.commit();rng=np.random.default_rng(231);names=['SX-31A 多类图谱评议','SX-31B 类别失衡评议','SX-31C 单类边界评议'];categories=['砂岩','粉砂岩','泥岩','碳酸盐岩'];raters=['标记者甲','标记者乙','标记者丙']
  for index,name in enumerate(names):
   if db.scalar(select(AgreementStudy).where(AgreementStudy.name==name)):continue
   study=AgreementStudy(name=name,filename=f'sx-core-panel-{index+1}-202611.json',description=['固定面板独立标记，类别较均衡','主类占比高；机会基线须一起读','全单类Pe=1，κ未定义，不当作κ1'][index],categories=categories,raters=raters);db.add(study);db.flush()
   for i in range(120):
    item=Specimen(study_id=study.id,reference=f'SX{index+1}-IMG-{i+1:03d}',description='匿名独立岩芯图像编号；非真实现场样本');db.add(item);db.flush();latent=int(rng.choice(4,p=[.25]*4 if index==0 else [.88,.04,.04,.04])) if index<2 else 0
    for rater in raters:
     label=latent if index==2 or rng.random()<(.84 if index==0 else .94) else int(rng.choice([c for c in range(4) if c!=latent]));db.add(RaterVote(specimen_id=item.id,rater=rater,category=categories[label]))
   db.commit()
  run=db.scalar(select(AgreementRun).where(AgreementRun.name=='A研究固定面板口径核对'))
  if not run:
   study=db.scalar(select(AgreementStudy).where(AgreementStudy.name==names[0]));items=[row(s) for s in db.scalars(select(Specimen).where(Specimen.study_id==study.id))];ids=[s['id'] for s in items];votes=[row(v) for v in db.scalars(select(RaterVote).where(RaterVote.specimen_id.in_(ids)))];config={'bootstrap_repeats':400,'seed':231,'panel_scope':'fixed_three_raters'};snapshot=build_source_snapshot(row(study),items,votes,config);result=analyze_snapshot(snapshot);run=AgreementRun(study_id=study.id,name='A研究固定面板口径核对',config=config,source_snapshot=snapshot,queued_fingerprint=snapshot_fingerprint(snapshot),status='completed',result=result,kappa=result['kappa'],pbar=result['pbar'],pe=result['pe'],created_by='analyst@shanxu.demo');db.add(run);db.commit()
  if not db.scalar(select(ReviewMemo).where(ReviewMemo.name=='A研究分类边界复核初稿')):
   memo_snapshot=dict(run.result);memo_snapshot['batch']={'snapshot_version':run.source_snapshot.get('version'),'queued_fingerprint':run.queued_fingerprint,'current_fingerprint_at_memo':run.queued_fingerprint,'current_matches_queued_at_memo':True}
   db.add(ReviewMemo(run_id=run.id,name='A研究分类边界复核初稿',interpretation='κ是相对类别基率的一致性，不是与金标准对照的准确率。',next_step='固定原三位标记者，独立复核争议试样的类别定义与图谱边界。',result_snapshot=memo_snapshot,created_by='analyst@shanxu.demo'));db.commit()
  counts={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,AgreementStudy,Specimen,RaterVote,AgreementRun,ReviewMemo]};print(json.dumps(counts));return counts
if __name__=='__main__':seed()
