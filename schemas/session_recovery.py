# schemas/session_recovery.py
from typing import Optional, Dict
from pydantic import BaseModel

class CheckpointRequest(BaseModel):
    session_id: str
    candidate_id: str
    current_question: int
    answers: Dict[str, str]  # or whatever structure you use
    time_remaining: int
    status: str

class ResumeResponse(BaseModel):
    session_id: str
    candidate_id: str
    current_question: int
    answers: Dict[str, str]
    time_remaining: int
    status: str
