# models.py
from sqlalchemy import Column, String, Integer, JSON
from database import Base

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, nullable=False)
    current_question = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False, default={})
    time_remaining = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
