import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal
from routers import orders, riders, proposals, ocr, stream
from services.simulator import run_simulator


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(run_simulator(SessionLocal, stream.manager.broadcast))
    yield
    task.cancel()


app = FastAPI(title="OpsPilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router)
app.include_router(riders.router)
app.include_router(proposals.router)
app.include_router(ocr.router)
app.include_router(stream.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "OpsPilot backend is running"}
