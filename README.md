# 杉序岩芯标记一致性簿

杉序岩芯图谱研究组有17位标记分析员，由固定三位标记者对独立匿名岩芯图像分类。上游输入 `sx-core-panel-1-202611.json` 等逐人标签，本系统替代表格里的逐票计数与随意重采样，下游是负责人批准的类别边界复核说明。三个具体痛点是只报一致百分比、类别失衡的机会基线被忽略、按单票重采样破坏同一试样结构。

固定种子生成3项研究×120试样×3票=1080标签、四种岩相，分别覆盖多类评议、类别失衡、全单类未定义边界。数据为合成匿名图像编号，不含现场地质结论。Fleiss κ是相对类别基率的一致性，不是与金标准对照的准确率。

## 启动、环境和角色

```sh
cp .env.example .env
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.seed_demo
```

|入口|地址|
|---|---|
|浏览器|http://localhost:18235|
|API / Swagger|http://localhost:19235/docs|
|MySQL|127.0.0.1:17735|

|账号 / 密码|权限与主要页面|典型动作|
|---|---|---|
|admin@shanxu.demo / Shanxu2026!|六页、写入与审阅|批准或退回分类口径复核|
|analyst@shanxu.demo / Shanxu2026!|六页、导入/改票/运行/说明|修订逐票、排队；审批403|
|viewer@shanxu.demo / Shanxu2026!|六页只读、批准CSV|阅读逐票与结果、下载快照；写入403|

首次启动自动seed，手动独立执行也幂等，不覆盖用户改票、试样说明和复核意见。`.env.example`含三个端口、MYSQL_DATABASE/USER/PASSWORD/ROOT_PASSWORD、JWT_SECRET、SEED_DEMO、RATE_LIMIT_WRITES默认60。演示密码和JWT secret仅用于本地，部署须设置自己的值。

Compose恰好frontend/backend/worker/db/redis五服务，均有健康检查。Nginx `/api/`移除前缀后转发FastAPI，前端探针127.0.0.1；backend等待DB/Redis，worker再等待backend。Celery真队列保存运行JSON和数据库结果，共享artifacts卷。停止清除本题演示数据：`docker compose down -v --remove-orphans`。

## 标记分析员的一天

1. 09:00，秦砚登录“评议总览”，先看逐票格和类别基率，区分一致性与准确率。
2. 09:10，在“试样与逐票”选择 `SX-31A 多类图谱评议`，核对文件 `sx-core-panel-1-202611.json`，如 `SX1-IMG-001` 的固定三票。
3. 核对原面板“标记者甲 / 标记者乙 / 标记者丙”，以及声明类别顺序“砂岩 / 粉砂岩 / 泥岩 / 碳酸盐岩”。每人每试样恰一票；缺票、重复人、未知类会拒绝。试样补注和改票均留痕。
4. 在“固定面板配置”预先设B=400、seed=231，整个研究全部独立试样参与；队列按整试样计数行重采样。
5. A研究实际N120/360票，Pbar=0.7083333333、Pe=0.2511265432、κ=0.6105260989。类别总票97/95/84/84，一起解释机会基线。
6. 读400有效/0退化重复和经验percentile区间[0.5296296698,0.6836294491]，可展开每次抽取行索引、κ与失败理由。它只在固定面板与iid试样条件下解释。
7. 对照“单类边界评议”：全部票同类时Pe=1、κ未定义，worker会失败，不把它标成κ1。全一致但有多类时κ可以1。
8. 在“口径复核”写争议试样的类别边界与独立复核行动，保持原三位标记者。说明冻结整份统计与bootstrap快照。
9. 负责人纪岚批准/退回；观察员陶野下载批准CSV（κ、Pbar、Pe、有效/退化数、区间、逐试样P和计数）。重复审批409，后续改票不改写已有快照；过程留痕核对全部动作。

## Fleiss κ与整行bootstrap口径

设N个试样、r=3个固定标记者、C个预先声明的名义类别，nᵢⱼ是试样i被分到类别j的票数。每行总数必须3：

`Pᵢ = Σⱼ nᵢⱼ(nᵢⱼ−1) / [r(r−1)]`

`Pbar = mean(Pᵢ)`，`pⱼ = Σᵢ nᵢⱼ/(Nr)`，`Pe = Σⱼ pⱼ²`，`κ = (Pbar−Pe)/(1−Pe)`。

后端用整数计数和Fraction计算核心比值，先判断Pe恰等于1再转JSON浮点。Pe=1未定义；全一致多类别κ1；未出现类别保留在声明顺序中，计数0。κ可为负，不裁成0，也不解读为识别准确率。试样级P和类别基率与κ同时保存。

Bootstrap固定seed，B400–1000次；每次有放回抽N个完整计数行，保留每个抽取索引。每行原三票绑定，不能按单票抽，也不能把标记者当新抽样单位。每次重新计算κ；Pe=1的重复保存null κ、原抽取索引和失败原因，未补抽替换。

有效数/B≥90%才报告有效重复κ的2.5%和97.5%线性percentile经验区间（NumPy quantile method=linear）；不足90%保留全部重复并明确“暂不报告”。这是预先设定的可报告门槛，不是有限样本精确覆盖保证。条件是试样iid、面板固定，不含抽取新标记者的不确定性；空间相关、共享图像或类别定义改变会影响解释。

手算例四试样二类计数[3,0]/[2,1]/[1,2]/[0,3]：Pbar=2/3、Pe=.5、κ=1/3。B400/seed231得到397有效、3退化，经验区间约[-.3714285714,1]。两试样[3,0]/[0,3]虽κ1，但同参数只有205有效/195退化，不报告区间。真实API与浏览器都验证了这些边界。

MySQL的κ/Pbar/Pe列均用DOUBLE(asdecimal=False)，保持Python float，避免默认Decimal十位小数转换损失；API逐项与JSON结果比到1e-15并查询实际列类型。

## 结构与校验

77个有职责的Python/TS/Vue/CSS源文件（不计空包、依赖和dist）。五实体AgreementStudy → Specimen → RaterVote → AgreementRun → ReviewMemo贯穿ORM/schema/service/routes、前端API/store和六页：评议总览、试样与逐票、固定面板配置、κ与重采样、口径复核、过程留痕。

前端 `src/{api,stores,types,components/common,hooks,pages,router,utils,constants}`；后端 `src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}`，另scripts/seed_demo.py与migrations/。VoteMatrix、AgreementSummary、CategoryMargins、RunList多页复用，BootstrapStrip展示后端实际频数和经验区间；useTask/useRoute和format工具处理交互。

角色Role、运行RunStatus、审阅MemoStatus位于 `backend/src/constants/enums.py`，前端对应 `frontend/src/constants/enums.ts`。JWT授权、审计、RequestID/Error/Redis写限流三个中间件形成横切链路。配额按令牌摘要或无令牌IP与分钟计数，默认60写请求、超限429含Retry-After；计数服务不可用503，健康GET不计。审批行锁限制draft只能审一次，批准导出取result_snapshot。

2–240试样、声明2–6唯一类别、固定3位唯一标记者；每试样同一面板各一票。重复试样、重复人、缺票、未知类别和非法B/seed拒绝；安全422不回显NaN等非法input。全单类数据可存底稿，但κ计算明确失败，不伪造结果。指纹按试样编号/票键排序，行序稳定，对票、试样说明、类别/面板顺序和参数敏感。

|层|技术|
|---|---|
|前端|Vue3 / TypeScript / Vite6.4.6；Public Sans+Noto Serif SC；炭灰逐票图谱|
|后端|Python3.11 / FastAPI / SQLAlchemy / MySQL8|
|队列|Celery5.4 / Kombu5.4.2 / Redis7，worker并发1|
|数值|整数/Fraction Fleiss κ、整试样行bootstrap、真实频数SVG|

本地前端 `cd frontend && npm ci && npm run dev`；`npm run build`执行vue-tsc与Vite。后端安装requirements并设置DATABASE_URL/REDIS_URL/JWT_SECRET后运行uvicorn。当前用ORM create_all建表，migrations提供初始结构说明，不声称生产版本迁移链。许可证MIT，见LICENSE。

实际验收见批次 `test-artifacts/gb-0031/TESTING.md`，测试脚本、关键JSON、CSV、PNG、原始.log与源码分离。未做外部真实岩相准确率验证、生产压力或完整无障碍审计。令牌/IP分钟限流不是生产抗滥用全链路，重新登录可获得新令牌计数。Google字体断网时回退本地字体。任何复核方案仍需试验员结合图谱定义执行，不提供地质因果或现场风险保证。
