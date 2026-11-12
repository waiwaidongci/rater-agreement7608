from pydantic import BaseModel,Field,ConfigDict
from .specimen import SpecimenInput
class StudyInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 name:str=Field(min_length=2,max_length=150)
 filename:str=Field(min_length=2,max_length=180)
 description:str=Field(default='',max_length=3000)
 categories:list[str]=Field(min_length=2,max_length=6)
 raters:list[str]=Field(min_length=3,max_length=3)
 specimens:list[SpecimenInput]=Field(min_length=2,max_length=240)
