from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,JSON,Text,DateTime
from sqlalchemy.dialects.mysql import DOUBLE
from datetime import datetime,timezone
from src.config.database import Base
class AgreementRun(Base):
 __tablename__='agreement_runs'
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('agreement_studies.id'))
 name:Mapped[str]=mapped_column(String(180),unique=True)
 config:Mapped[dict]=mapped_column(JSON)
 # 排队时刻冻结的试样、逐票与参数快照；worker只按该批次计算，之后的改票/补注不影响本运行
 source_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
 # 排队时与执行时各算一次指纹，便于核对资料批次；当前资料已变更时两者不同
 queued_fingerprint:Mapped[str|None]=mapped_column(String(64),nullable=True)
 status:Mapped[str]=mapped_column(String(24),default='queued')
 result:Mapped[dict|None]=mapped_column(JSON,nullable=True)
 error:Mapped[str|None]=mapped_column(Text,nullable=True)
 kappa:Mapped[float|None]=mapped_column(DOUBLE(asdecimal=False),nullable=True)
 pbar:Mapped[float|None]=mapped_column(DOUBLE(asdecimal=False),nullable=True)
 pe:Mapped[float|None]=mapped_column(DOUBLE(asdecimal=False),nullable=True)
 created_by:Mapped[str]=mapped_column(String(120))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
