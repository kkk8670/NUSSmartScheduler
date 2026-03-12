# tools/knowledge_tool.py

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from app.core.config import settings
from app.core.logging import jlog

FAKE_CORPUS = [
    {"url": "mem://nus/com1", "text": "COM1 lecture theaters & tutorial rooms scheduling guide.", "score": 0.62},
    {"url": "mem://nus/pgp", "text": "PGP residence shuttle and walking times to COM1.", "score": 0.55},
    {"url": "mem://nus/lib", "text": "NUS library quiet study areas open until 21:30.", "score": 0.58},
    {"url": "mem://nus/bus", "text": "Internal shuttle A1/A2 timings across Kent Ridge campus.", "score": 0.51},
]

try:
    from app.agent.mem_store import search_chunks
except Exception:
    search_chunks = None

# 1) 定义输入
class KnowledgeInput(BaseModel):
    query: str = Field(..., description="User query or task that needs external knowledge")

# 2) 核心逻辑封装为函数
def knowledge_tool_func(query: str) -> Dict[str, Any]:
    notes = []
    candidates = []

    if not settings.KNOWLEDGE_ENABLE:
        notes.append("[Knowledge] disabled")
        return {"candidates": [], "notes": notes}

    err = None

    # 1) 向向量库搜索
    try:
        if search_chunks is not None:
            rows = search_chunks(user_id="u123", query=query, topk=10)
            candidates = [{"url": "mem", "text": t, "score": float(s)} for (t, s) in rows]
    except Exception as e:
        err = str(e)

    # 2) fallback
    if (not candidates) and settings.KNOWLEDGE_FAKE_FALLBACK:
        notes.append(f"[Knowledge] fallback=FAKE_CORPUS" + (f" (err={err})" if err else ""))
        candidates = FAKE_CORPUS.copy()

    # 不做 episodic merge（由单独 memory_agent_tool 来做更好，否则混乱）

    jlog("knowledge_tool_done", got=len(candidates))

    return {
        "candidates": candidates,
        "notes": notes
    }

# 3) 封装成 LangChain Tool
knowledge_agent_tool = StructuredTool.from_function(
    name="knowledge_agent_tool",
    description="Search external knowledge or campus info relevant to the user's query.",
    func=lambda query: knowledge_tool_func(query),
    args_schema=KnowledgeInput,
)
