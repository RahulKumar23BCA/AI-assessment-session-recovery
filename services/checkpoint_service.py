# services/checkpoint_service.py
from sqlalchemy.orm import Session
from models import Session as SessionModel


def save_session(db: Session, data: dict) -> SessionModel:
    # Try to fetch existing session
    db_session = db.query(SessionModel).filter(SessionModel.session_id == data["session_id"]).first()

    if db_session:
        # Update existing session
        db_session.candidate_id = data["candidate_id"]
        db_session.current_question = data["current_question"]
        db_session.answers = data["answers"]
        db_session.time_remaining = data["time_remaining"]
        db_session.status = data["status"]
    else:
        # Create new session
        db_session = SessionModel(**data)
        db.add(db_session)

    db.commit()
    db.refresh(db_session)
    return db_session
