from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DebugResult(BaseModel):
    root_cause: str
    solutions: List[Dict[str, Any]]
    fix_instructions: str
    confidence_score: float
    agent_metrics: Dict[str, Any]
    execution_time: float

class RankedSolution(BaseModel):
    rank: int
    title: str
    description: str
    steps: List[str]
    code_changes: List[dict] = Field(default_factory=list)
    confidence: float
    sources: List[str] = Field(default_factory=list)
    why_ranked_here: str
    trade_offs: List[str] = Field(default_factory=list)
