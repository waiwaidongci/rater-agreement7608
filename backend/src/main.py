import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from src.config.database import Base,engine
from src.config.settings import SEED_DEMO,REDIS_URL
from src.models import *
from src.middlewares.request_id import RequestIDMiddleware
from src.middlewares.errors import ErrorMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import auth,source,runs,memos,audit
@asynccontextmanager
async def lifespan(app):
 Base.metadata.create_all(engine)
 if SEED_DEMO:
  try:
   from scripts.seed_demo import seed
   seed()
  except Exception:logging.exception('seed failure; startup continues')
 yield
app=FastAPI(title='杉序岩芯标记一致性簿',lifespan=lifespan)
@app.exception_handler(RequestValidationError)
async def invalid_input(request,error):return JSONResponse({'detail':[{'loc':e['loc'],'message':e['msg'],'type':e['type']} for e in error.errors()]},status_code=422)
app.add_middleware(ErrorMiddleware);app.add_middleware(RateLimitMiddleware);app.add_middleware(RequestIDMiddleware)
for route in (auth,source,runs,memos,audit):app.include_router(route.router)
@app.get('/health')
def health():
 with engine.connect() as connection:connection.execute(text('select 1'))
 Redis.from_url(REDIS_URL).ping();return {'status':'ok'}
