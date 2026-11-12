from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,UniqueConstraint
from src.config.database import Base
class RaterVote(Base):
 __tablename__='rater_votes'
 __table_args__=(UniqueConstraint('specimen_id','rater'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 specimen_id:Mapped[int]=mapped_column(ForeignKey('specimens.id'))
 rater:Mapped[str]=mapped_column(String(80))
 category:Mapped[str]=mapped_column(String(80))
