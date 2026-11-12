from pydantic import BaseModel,Field,ConfigDict
from .vote import VoteInput
class SpecimenInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 reference:str=Field(min_length=1,max_length=100)
 description:str=Field(default='',max_length=1000)
 votes:list[VoteInput]=Field(min_length=3,max_length=3)
class SpecimenPatch(BaseModel):
 description:str=Field(max_length=1000)
