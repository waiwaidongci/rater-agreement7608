from pydantic import BaseModel,Field,ConfigDict
class VoteInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 rater:str=Field(min_length=1,max_length=80)
 category:str=Field(min_length=1,max_length=80)
class VotePatch(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 category:str=Field(min_length=1,max_length=80)
