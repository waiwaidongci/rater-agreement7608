"""端到端验证：排队冻结资料批次、改票穿插、幂等重投、中断恢复、旧运行缺资料提示。
用 SQLite 临时库 + 直接调用服务/worker 任务函数，不依赖 MySQL/Redis/Docker。"""
import os,sys,tempfile,json
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(prefix='agtest-'),'test.db')
os.environ['ARTIFACT_DIR']=tempfile.mkdtemp(prefix='agart-')
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))

from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import User,AgreementStudy,Specimen,RaterVote,AgreementRun,ReviewMemo
from src.utils.security import hash_password
from src.utils.serialize import row
from src.services.source import create_study,edit_vote,edit_item,source_data
from src.services.runs import create_run,requeue_run,batch_status
from src.services.analysis import analyze_snapshot
from src.services import runs as runs_service
from src import worker
from src.schemas.study import StudyInput
from src.schemas.run import RunInput
from src.schemas.vote import VotePatch
from src.schemas.specimen import SpecimenPatch
from src.schemas.memo import MemoInput,ApprovalInput
from src.services.memos import create_memo,approve_memo
from src.controllers.export import export_memo
from src.services.fingerprint import fingerprint
from fastapi import HTTPException

# 真实 Celery 任务函数（__call__ 即同步执行任务体）；任务在独立 DB 会话运行，与真实 worker 进程一致
real_task=worker.app.tasks['rater.analyze']
def execute(id):
 """在全新解释器会话边界外执行 worker 任务：确保排队/重投的提交对任务可见。"""
 real_task(id)

Base.metadata.create_all(engine)
PASS=[];FAIL=[]
def check(name,cond,detail=''):
 (PASS if cond else FAIL).append(name);print(('  ✓ ' if cond else '  ✗ ')+name+((' — '+str(detail)) if detail and not cond else ''))

with SessionLocal() as db:
 db.add(User(email='analyst@shanxu.demo',name='analyst',role='analyst',password_hash=hash_password('x')))
 db.add(User(email='viewer@shanxu.demo',name='viewer',role='viewer',password_hash=hash_password('x')))
 db.add(User(email='admin@shanxu.demo',name='admin',role='admin',password_hash=hash_password('x')));db.commit()

class FakeTask:
 def __init__(self):self.calls=[]
 def delay(self,id):self.calls.append(id)
fake=FakeTask()
worker.analyze_run=fake  # create_run/requeue_run 内 `from src.worker import analyze_run` 取到该假对象

def make_study(db,prefix='T'):
 data=StudyInput(name=prefix+'研究',filename=prefix+'.json',description='d',
  categories=['砂岩','粉砂岩'],raters=['标记者甲','标记者乙','标记者丙'],
  specimens=[{'reference':f'{prefix}-{i:03d}','description':'','votes':[
   {'rater':'标记者甲','category':'砂岩'},{'rater':'标记者乙','category':c},{'rater':'标记者丙','category':'砂岩'}]}
   for i,c in enumerate(['砂岩','粉砂岩','砂岩','粉砂岩'])])
 return create_study(db,data,'analyst@shanxu.demo')

def run_input(study_id,name,B=400,seed=231):
 return RunInput(study_id=study_id,name=name,bootstrap_repeats=B,seed=seed,panel_scope='fixed_three_raters')

# ---------- 场景1：排队后改票/补注，worker 仍按排队原批计算 ----------
print('\n[1] 排队冻结：改票穿插排队，结果对应排队原批')
with SessionLocal() as db:
 study=make_study(db);sid=study['id']
 before_study,before_items,before_votes=source_data(db,sid)
 r1=create_run(db,run_input(sid,'运行1-排队原批'),'analyst@shanxu.demo');rid=r1['id']
 check('排队即写快照（含12票/4试样/参数）',r1['source_snapshot'] is not None and len(r1['source_snapshot']['votes'])==12 and len(r1['source_snapshot']['specimens'])==4)
 check('排队即写64位批次指纹',bool(r1['queued_fingerprint']) and len(r1['queued_fingerprint'])==64)
 check('快照结构完整',set(r1['source_snapshot'])=={'version','study','specimens','votes','config'})
 check('任务已投递',fake.calls[-1]==rid)
 # 排队后改票 + 补注
 _,items,_=source_data(db,sid)
 target=db.scalars(select(RaterVote).where(RaterVote.rater=='标记者乙')).first()
 edit_vote(db,target.id,VotePatch(category='砂岩'),'analyst@shanxu.demo')
 edit_item(db,items[0]['id'],SpecimenPatch(description='排队后补注'),'analyst@shanxu.demo')
 run_row=db.get(AgreementRun,rid)
 bs=batch_status(db,run_row)
 check('检测到排队后资料漂移',bs['current_matches_queued'] is False)
 check('快照冻结的仍是排队原票',r1['source_snapshot']['votes']==[dict(v) for v in before_votes])
 check('快照冻结的是排队原补注（空）',all(s['description']=='' for s in r1['source_snapshot']['specimens']))

with SessionLocal() as db:
 run_before=row(db.get(AgreementRun,rid))
# worker 在独立会话领取（真实 Celery 进程边界）
execute(rid)
with SessionLocal() as db:
 run_after=db.get(AgreementRun,rid)
 check('运行完成',run_after.status=='completed',run_after.error or '')
 expected=analyze_snapshot(run_before['source_snapshot'])
 check('结果=按排队快照独立重算',run_after.result['fingerprint']==expected['fingerprint'])
 check('结果指纹=排队批次指纹（原批）',run_after.result['fingerprint']==run_after.queued_fingerprint)
 cur_study,cur_items,cur_votes=source_data(db,run_after.study_id)
 cur_fp=fingerprint(cur_study,cur_items,cur_votes,run_after.config)
 check('当前资料指纹≠结果指纹（未被现状污染）',cur_fp!=run_after.result['fingerprint'])
 check('κ/pbar/pe 已落库',isinstance(run_after.kappa,float) and isinstance(run_after.pbar,float) and isinstance(run_after.pe,float))
 art=os.path.join(os.environ['ARTIFACT_DIR'],f'rater-{rid}.json')
 check('artifact JSON 与库内结果一致',os.path.exists(art) and json.load(open(art))['fingerprint']==run_after.result['fingerprint'])

# ---------- 场景2：重复执行同一任务幂等 ----------
print('\n[2] 幂等：重复执行同一任务不新增结果')
with SessionLocal() as db:
 run=db.get(AgreementRun,rid);kw_result,kw_kappa=run.result,run.kappa
 n1=db.scalar(select(func.count()).select_from(AgreementRun))
execute(rid);execute(rid)
with SessionLocal() as db:
 run=db.get(AgreementRun,rid)
 n2=db.scalar(select(func.count()).select_from(AgreementRun))
 check('运行数不增加',n1==n2==1)
 check('结果与指标未被改写',run.result==kw_result and run.kappa==kw_kappa)
 check('状态仍 completed',run.status=='completed')

# ---------- 场景3：中断恢复 ----------
print('\n[3] 中断恢复：running 滞留 → 重投 → 原批完成，不新增运行')
with SessionLocal() as db:
 study=make_study(db,prefix='R');r2=create_run(db,run_input(study['id'],'运行2-中断恢复'),'analyst@shanxu.demo');rid2=r2['id']
 stuck=db.get(AgreementRun,rid2);stuck.status='running';db.commit()
 out=requeue_run(db,rid2,'analyst@shanxu.demo')
 check('重投回 queued 且 id 不变',out['id']==rid2 and out['status']=='queued')
 check('重投再次入队',fake.calls[-1]==rid2)
 n1=db.scalar(select(func.count()).select_from(AgreementRun))
# 重投提交已关闭，worker 在独立会话领取（与真实 Celery worker 进程一致）
execute(rid2)
with SessionLocal() as db:
 n2=db.scalar(select(func.count()).select_from(AgreementRun))
 run2=db.get(AgreementRun,rid2)
 check('恢复后完成且未新增运行',run2.status=='completed' and n1==n2,run2.error)
 check('恢复结果对应排队指纹',run2.result['fingerprint']==run2.queued_fingerprint)
 try:
  requeue_run(db,rid2,'analyst@shanxu.demo');check('完成任务拒绝重投(409)',False)
 except HTTPException as e:check('完成任务拒绝重投(409)',e.status_code==409)
 # queued 滞留（消息丢失）也可重投；重复重投不新增运行
 study_q=make_study(db,prefix='Q');rq=create_run(db,run_input(study_q['id'],'运行Q-消息丢失'),'analyst@shanxu.demo');ridq=rq['id']
 outq=requeue_run(db,ridq,'analyst@shanxu.demo')
 check('queued 滞留可重投且 id 不变',outq['id']==ridq and outq['status']=='queued')
 nq1=db.scalar(select(func.count()).select_from(AgreementRun))
 requeue_run(db,ridq,'analyst@shanxu.demo')
 nq2=db.scalar(select(func.count()).select_from(AgreementRun))
 check('重复重投不新增运行',nq1==nq2)
 # 模拟同一任务被投递两次：两次执行只有一次真正计算
 execute(ridq);execute(ridq)
 rq_after=db.get(AgreementRun,ridq)
 check('重复投递仅一次计算，结果对应原批',rq_after.status=='completed' and rq_after.result['fingerprint']==rq_after.queued_fingerprint)
 study3=make_study(db,prefix='F');r3=create_run(db,run_input(study3['id'],'运行3-失败'),'analyst@shanxu.demo')
 rf=db.get(AgreementRun,r3['id']);rf.status='failed';db.commit()
 try:
  requeue_run(db,r3['id'],'analyst@shanxu.demo');check('失败任务拒绝重投(409)',False)
 except HTTPException as e:check('失败任务拒绝重投(409)',e.status_code==409)

# ---------- 场景4：旧运行缺快照 ----------
print('\n[4] 旧运行缺原始资料：明确失败/阻止，不以现状补齐')
with SessionLocal() as db:
 study=make_study(db,prefix='O');r4=create_run(db,run_input(study['id'],'运行4-旧版无快照'),'analyst@shanxu.demo');rid4=r4['id'];sid4=study['id']
 legacy=db.get(AgreementRun,rid4);legacy.source_snapshot=None;legacy.queued_fingerprint=None;legacy.status='queued';db.commit()
execute(rid4)
with SessionLocal() as db:
 legacy=db.get(AgreementRun,rid4)
 check('缺快照 worker 失败',legacy.status=='failed')
 check('失败信息明确且要求重新排队',bool(legacy.error) and '重新排队' in legacy.error and '快照' in legacy.error,legacy.error)
 check('未产生任何结果',legacy.result is None and legacy.kappa is None)
 check('批次状态 missing_snapshot',batch_status(db,legacy)['missing_snapshot'] is True)
 # 模拟历史遗留的已完成旧运行：结果保留可查看，但不能建说明
 legacy.status='completed';legacy.error=None
 legacy.result={'kappa':0.1,'pbar':0.5,'pe':0.4,'bootstrap':{'valid_repeats':400,'invalid_repeats':0,'interval':[0,1]},'items':[],'source_study':row(db.get(AgreementStudy,sid4)),'categories':['砂岩','粉砂岩'],'raters':['标记者甲','标记者乙','标记者丙'],'fingerprint':'legacy','specimen_count':4};db.commit()
 try:
  create_memo(db,MemoInput(run_id=rid4,name='不应建成的说明',interpretation='解释文本内容',next_step='复核行动安排'),'analyst@shanxu.demo');check('旧运行阻止建说明(422)',False)
 except HTTPException as e:check('旧运行阻止建说明(422)',e.status_code==422 and '快照' in e.detail)

# ---------- 场景5：复核说明批次核对与导出 ----------
print('\n[5] 复核说明冻结批次、可核对，审批/导出留痕')
with SessionLocal() as db:
 run=db.get(AgreementRun,rid)
 memo=create_memo(db,MemoInput(run_id=rid,name='说明1-原批',interpretation='解释文本内容',next_step='复核行动安排'),'analyst@shanxu.demo')
 b=memo['result_snapshot']['batch']
 check('说明内嵌批次块',b['queued_fingerprint']==run.queued_fingerprint and bool(b['snapshot_version']))
 check('建说明时留痕“与现状不一致”',b['current_matches_queued_at_memo'] is False)
 approve_memo(db,memo['id'],ApprovalInput(status='approved',review_note='同意口径'),'admin@shanxu.demo')
 memo_after=db.get(ReviewMemo,memo['id'])
 check('审批后说明批次不变',memo_after.result_snapshot['batch']['queued_fingerprint']==run.queued_fingerprint)
 try:
  approve_memo(db,memo['id'],ApprovalInput(status='approved',review_note='再次审批'),'admin@shanxu.demo');check('重复审批409',False)
 except HTTPException as e:check('重复审批409',e.status_code==409)
 resp=export_memo(db,memo['id'],'viewer@shanxu.demo')
 body=resp.body.decode()
 check('CSV 含排队指纹与漂移核对',run.queued_fingerprint in body and '排队后资料已变更' in body)

# ---------- 场景6：后续编辑只影响新运行 ----------
print('\n[6] 改票后新运行取新批次，旧运行保持原批')
with SessionLocal() as db:
 r_new=create_run(db,run_input(1,'运行5-改票后新批'),'analyst@shanxu.demo');new_id=r_new['id']
execute(new_id)
with SessionLocal() as db:
 new=db.get(AgreementRun,new_id);old=db.get(AgreementRun,rid)
 check('新旧运行批次指纹不同',new.queued_fingerprint!=old.queued_fingerprint)
 check('新运行按当前资料冻结',new.result['fingerprint']==new.queued_fingerprint)
 check('新运行与当前资料一致',batch_status(db,new)['current_matches_queued'] is True)
 check('旧运行仍标记漂移',batch_status(db,old)['current_matches_queued'] is False)

# ---------- 场景7：参数参与批次指纹 ----------
print('\n[7] 参数批次：B/seed 不同则指纹不同')
with SessionLocal() as db:
 ra=create_run(db,RunInput(study_id=1,name='运行6a',bootstrap_repeats=400,seed=231,panel_scope='fixed_three_raters'),'analyst@shanxu.demo')
 rb=create_run(db,RunInput(study_id=1,name='运行6b',bootstrap_repeats=500,seed=231,panel_scope='fixed_three_raters'),'analyst@shanxu.demo')
 check('B 不同→批次指纹不同',ra['queued_fingerprint']!=rb['queued_fingerprint'])

# ---------- 场景8：队列不可用降级 ----------
print('\n[8] 队列不可用时 503 降级，不留 queued 假任务')
worker.analyze_run=type('Broken',(),{'delay':lambda self,id:(_ for _ in ()).throw(RuntimeError('redis down'))})()
with SessionLocal() as db:
 try:
  create_run(db,run_input(1,'运行7-队列挂'),'analyst@shanxu.demo');check('队列不可用返回503',False)
 except HTTPException as e:check('队列不可用返回503',e.status_code==503)
 broken=db.scalar(select(AgreementRun).where(AgreementRun.name=='运行7-队列挂'))
 check('降级运行 failed 且带提示',broken is not None and broken.status=='failed' and '队列不可用' in (broken.error or ''))

print(f'\n==== 通过 {len(PASS)} 项，失败 {len(FAIL)} 项 ====')
if FAIL:
 print('FAILED:',FAIL);sys.exit(1)
print('ALL PASS')
