from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from schemas.session_recovery import CheckpointRequest, ResumeResponse
from services.checkpoint_service import save_session
from services.recovery_service import get_session_by_id

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/checkpoint", response_model=ResumeResponse)
def checkpoint(request: CheckpointRequest, db: Session = Depends(get_db)):
    db_session = save_session(db, request.dict())
    return ResumeResponse(
        session_id=db_session.session_id,
        candidate_id=db_session.candidate_id,
        current_question=db_session.current_question,
        answers=db_session.answers,
        time_remaining=db_session.time_remaining,
        status=db_session.status,
    )

@router.get("/resume/{session_id}", response_model=ResumeResponse)
def resume_session(session_id: str, db: Session = Depends(get_db)):
    db_session = get_session_by_id(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ResumeResponse(
        session_id=db_session.session_id,
        candidate_id=db_session.candidate_id,
        current_question=db_session.current_question,
        answers=db_session.answers,
        time_remaining=db_session.time_remaining,
        status=db_session.status,
    )

@router.get("/test-session-route")
def test_session_route():
    return {"msg": "session router is loaded"}
