import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base
from app.db.base import engine
from app.api.v1 import (
    auth,
    orders,
)
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
)

# Allow requests from the different services
origins = [
    os.getenv("AUTH_SERVICE_BASE_URL", "http://localhost:8001"),
    os.getenv("INVENTORY_SERVICE_BASE_URL", "http://localhost:8002"),
    os.getenv("ORDER_SERVICE_BASE_URL", "http://localhost:8003"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def index():
    return {"message": "ORDER-SERVICE MICROSERVICE API"}

app.include_router(auth.router)
app.include_router(orders.router)
