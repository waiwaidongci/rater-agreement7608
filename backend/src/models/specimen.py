from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Text,UniqueConstraint
from src.config.database import Base
class Specimen(Base):
 __tablename__='specimens'
 __table_args__=(UniqueConstraint('study_id','reference'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('agreement_studies.id'))
 reference:Mapped[str]=mapped_column(String(100))
 description:Mapped[str]=mapped_column(Text,default='')
