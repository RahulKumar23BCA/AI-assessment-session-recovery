from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routes.session_recovery import router

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Assessment Session Recovery")

@app.get("/ping")
def ping():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/session", tags=["Session Recovery"])
