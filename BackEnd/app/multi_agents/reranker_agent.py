
from typing import Any, Dict, List
from difflib import SequenceMatcher
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

class RerankInput(BaseModel):
    query: str = Field(..., description="The user's query/context")
    candidates: List[Dict[str, Any]] = Field(..., description="List of candidates with 'text' and 'score'")

def rerank_candidates(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score_cand(c: Dict[str, Any]) -> float:
        original_score = float(c.get("score", 0.0))
        text = c.get("text", "")
        if not text:
            return original_score
        sim = SequenceMatcher(None, query.lower(), text.lower()).ratio()
        return 0.7 * original_score + 0.3 * sim

    ranked = sorted(candidates, key=score_cand, reverse=True)
    return ranked

def _reranker_tool_func(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    return rerank_candidates(query, candidates)

reranker_agent_tool = StructuredTool.from_function(
    name="reranker_agent_tool",
    description=(
        "Re-rank memory or knowledge candidates based on their semantic score "
        "and similarity to the query. "
        "Use this after memory or knowledge retrieval when the order may not be optimal."
    ),
    func=lambda query, candidates: _reranker_tool_func(query, candidates),
    args_schema=RerankInput,
)
