from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from typing import Any, Dict, List

# === 1) 定义输入模型 ===
class MemoryToolInput(BaseModel):
    query: str = Field(..., description="User query or context for memory lookup")

# === 2) 把原来的逻辑提取为函数 ===
def memory_tool_func(query: str) -> Dict[str, Any]:
    from ..agent.mem_store import search_chunks
    from ..core.config import settings

    notes = []
    preferences = []
    episodic = []

    # 1) preference memory lookup
    if settings.MEMORY_ENABLE:
        try:
            rows_pref = search_chunks(user_id="u123", query="preference", k=5)
            if rows_pref:
                preferences = rows_pref
        except Exception as e:
            notes.append(f"[Memory] pref_err={e}")
    else:
        notes.append("[Memory] disabled")

    # 2) episodic memory lookup
    try:
        rows_epi = search_chunks(user_id="u123", query=query, k=8)
        episodic = rows_epi
    except Exception as e:
        notes.append(f"[Memory] episodic_err={e}")
        episodic = []

    # 3) fallback
    if not preferences and settings.MEMORY_FAKE_FALLBACK:
        notes.append("[Memory] fallback=DEFAULT_PREFS")
        preferences = [
            {"text": "Walk threshold 12 min"},
            {"text": "Preferred Buildings: COM1, Central Library"}
        ]

    # 4) return structured result
    return {
        "preferences": preferences,
        "memories": episodic,
        "notes": notes
    }

# === 3) 创建 Tool ===
memory_agent_tool = StructuredTool.from_function(
    name="memory_agent_tool",
    description="Retrieve user preferences and episodic memories related to the query.",
    func=lambda query: memory_tool_func(query),
    args_schema=MemoryToolInput,
)
