from fastapi import FastAPI
from .database import engine, Base
from . import routes

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(routes.router)
