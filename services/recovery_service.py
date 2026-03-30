# services/recovery_service.py
from sqlalchemy.orm import Session
from models import Session as SessionModel


def get_session_by_id(db: Session, session_id: str) -> SessionModel | None:
    return db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
