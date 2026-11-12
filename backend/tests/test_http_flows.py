"""HTTP 层验证：真实 FastAPI 路由/鉴权/序列化，SQLite 库；不含需 Redis 的限流中间件。"""
import os,sys,tempfile
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(prefix='aghttp-'),'http.db')
os.environ['ARTIFACT_DIR']=tempfile.mkdtemp(prefix='aghttpart-')
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from starlette.testclient import TestClient
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import User,AgreementRun,RaterVote,Specimen,ReviewMemo
from src.utils.security import hash_password
from src.routes import auth,source,runs,memos,audit
from src import worker
from src.schemas.study import StudyInput
from src.schemas.run import RunInput

app=FastAPI()
for r in (auth,source,runs,memos,audit):app.include_router(r.router)
Base.metadata.create_all(engine)
PASS=[];FAIL=[]
def check(n,c,d=''):(PASS if c else FAIL).append(n);print(('  ✓ ' if c else '  ✗ ')+n+((' — '+str(d)) if d and not c else ''))

with SessionLocal() as db:
 for role in ('admin','analyst','viewer'):
  db.add(User(email=f'{role}@shanxu.demo',name=role,role=role,password_hash=hash_password('pw')))
 db.commit()

class Fake:
 def __init__(self):self.calls=[]
 def delay(self,i):self.calls.append(i)
fake=Fake();worker.analyze_run=fake
real_task=worker.app.tasks['rater.analyze']

def login(c,role):
 r=c.post('/auth/login',json={'email':f'{role}@shanxu.demo','password':'pw'});check(f'{role} 登录200',r.status_code==200,r.status_code);return r.json()['token']
def hdr(t):return {'Authorization':'Bearer '+t}

with TestClient(app) as c:
 ta=login(c,'analyst');tv=login(c,'viewer');td=login(c,'admin')
 # 建研究
 payload={'name':'HTTP研究','filename':'h.json','description':'d','categories':['砂岩','粉砂岩'],'raters':['标记者甲','标记者乙','标记者丙'],
  'specimens':[{'reference':f'H-{i:03d}','description':'','votes':[{'rater':'标记者甲','category':'砂岩'},{'rater':'标记者乙','category':cat},{'rater':'标记者丙','category':'砂岩'}]} for i,cat in enumerate(['砂岩','粉砂岩','砂岩','粉砂岩'])]}
 r=c.post('/studies',json=payload,headers=hdr(ta));check('导入研究200',r.status_code==200,r.text);sid=r.json()['id']
 # 排队
 r=c.post('/runs',json={'study_id':sid,'name':'HTTP运行1','bootstrap_repeats':400,'seed':231,'panel_scope':'fixed_three_raters'},headers=hdr(ta))
 check('排队200且含快照/指纹',r.status_code==200 and r.json()['source_snapshot'] and r.json()['queued_fingerprint'],r.text)
 rid=r.json()['id']
 rg=c.get(f'/runs/{rid}',headers=hdr(ta)).json()
 check('GET 运行附 batch 且与当前一致',rg['batch']['has_snapshot'] is True and rg['batch']['current_matches_queued'] is True,str(rg.get('batch')))
 # viewer 不能排队/重投
 r=c.post('/runs',json={'study_id':sid,'name':'不应建成','bootstrap_repeats':400,'seed':1,'panel_scope':'fixed_three_raters'},headers=hdr(tv))
 check('viewer 排队 403',r.status_code==403,r.status_code)
 # 改票穿插
 votes=c.get('/votes',headers=hdr(ta)).json()
 v0=votes[0]
 r=c.patch(f"/votes/{v0['id']}",json={'category':'粉砂岩' if v0['category']=='砂岩' else '砂岩'},headers=hdr(ta));check('改票200',r.status_code==200,r.text)
 # GET /runs 带 batch 且标记漂移
 r=c.get('/runs',headers=hdr(ta));items=r.json();run1=[x for x in items if x['id']==rid][0]
 check('列表含 batch 且检测漂移',run1['batch']['current_matches_queued'] is False and run1['batch']['has_snapshot'] is True)
 # worker 执行
 real_task(rid)
 r=c.get(f'/runs/{rid}',headers=hdr(ta));j=r.json()
 check('单运行查询 completed 且结果=排队指纹',j['status']=='completed' and j['result']['fingerprint']==j['queued_fingerprint'],j.get('error'))
 check('结果指纹与当前资料指纹不同',j['result']['fingerprint']!=j['batch']['current_fingerprint'])
 # viewer 重投 403
 r=c.post(f'/runs/{rid}/requeue',headers=hdr(tv));check('viewer 重投403',r.status_code==403,r.status_code)
 # completed 重投 409
 r=c.post(f'/runs/{rid}/requeue',headers=hdr(ta));check('completed 重投409',r.status_code==409,r.status_code)
 # 建复核说明（漂移留痕）
 r=c.post('/memos',json={'run_id':rid,'name':'HTTP说明1','interpretation':'解释文本内容','next_step':'复核行动安排'},headers=hdr(ta))
 check('建说明200且批次块留痕漂移',r.status_code==200 and r.json()['result_snapshot']['batch']['current_matches_queued_at_memo'] is False,r.text)
 mid=r.json()['id']
 # analyst 审批 403
 r=c.patch(f'/memos/{mid}/approval',json={'status':'approved','review_note':'同意该口径'},headers=hdr(ta));check('analyst 审批403',r.status_code==403,r.status_code)
 # admin 批准 + 导出
 r=c.patch(f'/memos/{mid}/approval',json={'status':'approved','review_note':'同意该口径'},headers=hdr(td));check('admin 批准200',r.status_code==200,r.text)
 r=c.get(f'/memos/{mid}/export',headers=hdr(tv));check('批准CSV可下载含批次列',r.status_code==200 and '排队批次指纹' in r.text and '排队后资料已变更' in r.text,r.status_code)
 # 旧运行缺快照场景
 r=c.post('/runs',json={'study_id':sid,'name':'HTTP旧运行','bootstrap_repeats':400,'seed':7,'panel_scope':'fixed_three_raters'},headers=hdr(ta));lid=r.json()['id']
 with SessionLocal() as db:
  legacy=db.get(AgreementRun,lid);legacy.source_snapshot=None;legacy.queued_fingerprint=None;db.commit()
 r=c.get('/runs',headers=hdr(ta));legacy_j=[x for x in items if False]
 legacy_j=[x for x in r.json() if x['id']==lid][0]
 check('旧运行列表标记 missing_snapshot',legacy_j['batch']['missing_snapshot'] is True)
 real_task(lid)
 r=c.get(f'/runs/{lid}',headers=hdr(ta));lj=r.json()
 check('旧运行执行失败且提示明确',lj['status']=='failed' and '重新排队' in (lj['error'] or ''),lj.get('error'))
 # 模拟历史遗留：已完成但缺排队快照的旧运行，建说明应被专门拦截
 with SessionLocal() as db:
  lg=db.get(AgreementRun,lid);lg.status='completed';lg.error=None
  lg.result={'kappa':0.1,'pbar':0.5,'pe':0.4,'bootstrap':{'valid_repeats':400,'invalid_repeats':0,'interval':[0,1]},'items':[],'source_study':{'name':'HTTP研究'},'categories':['砂岩','粉砂岩'],'raters':['标记者甲','标记者乙','标记者丙'],'fingerprint':'legacy','specimen_count':4};db.commit()
 r=c.post('/memos',json={'run_id':lid,'name':'不应建成说明','interpretation':'解释文本内容','next_step':'复核行动安排'},headers=hdr(ta))
 check('对缺快照的已完成旧运行建说明422',r.status_code==422 and '快照' in r.json()['detail'],r.text)
 # 审计留痕可查
 r=c.get('/audit',headers=hdr(ta));check('审计含排队/改票/完成动作',r.status_code==200 and {'run.queued','vote.revised','run.completed'} <= {l['action'] for l in r.json()},r.status_code)

# 种子脚本幂等性：在独立子进程+独立库验证，避免与上方 HTTP 数据混计
print('\n[seed] seed_demo 幂等与快照完整性（独立库子进程）')
import subprocess,json
seed_db=os.path.join(tempfile.mkdtemp(prefix='agseed-'),'seed.db');seed_art=tempfile.mkdtemp(prefix='agseedart-')
seed_code="""
import os,sys,json
sys.path.insert(0,os.getcwd())
from sqlalchemy import select
from src.config.database import SessionLocal
from src.models import AgreementRun,ReviewMemo
from scripts.seed_demo import seed
c1=seed();c2=seed()
with SessionLocal() as db:
 run=db.scalar(select(AgreementRun).where(AgreementRun.name=='A研究固定面板口径核对'))
 memo=db.scalar(select(ReviewMemo).where(ReviewMemo.name=='A研究分类边界复核初稿'))
 print(json.dumps({'c1':c1,'c2':c2,'snapshot':bool(run.source_snapshot),'qfp':bool(run.queued_fingerprint),
  'fp_match':run.result['fingerprint']==run.queued_fingerprint,
  'memo_batch':memo.result_snapshot.get('batch',{}).get('queued_fingerprint')==run.queued_fingerprint},ensure_ascii=False))
"""
env=dict(os.environ,DATABASE_URL='sqlite:///'+seed_db,ARTIFACT_DIR=seed_art)
out=subprocess.run([sys.executable,'-I','-c',seed_code],cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]),env=env,capture_output=True,text=True)
check('seed 子进程正常退出',out.returncode==0,out.stderr[-400:])
if out.returncode==0:
 s=json.loads(out.stdout.strip().splitlines()[-1])
 check('两次 seed 计数一致',s['c1']==s['c2'],str(s['c1'])+' vs '+str(s['c2']))
 check('seed 运行带快照与排队指纹',s['snapshot'] and s['qfp'])
 check('seed 运行结果指纹=排队指纹',s['fp_match'])
 check('seed 说明快照含 batch',s['memo_batch'])
 check('seed 计数符合 README 口径',s['c1']['rater_votes']==1080 and s['c1']['specimens']==360 and s['c1']['agreement_studies']==3,str(s['c1']))

print(f'\n==== HTTP/seed 通过 {len(PASS)} 项，失败 {len(FAIL)} 项 ====')
if FAIL:print('FAILED:',FAIL);sys.exit(1)
print('ALL PASS')
