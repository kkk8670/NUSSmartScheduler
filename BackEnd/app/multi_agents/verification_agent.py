
from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
import json

try:
    from app.agent.mem_store import insert_chunk
except Exception:
    insert_chunk = None

try:
    from app.core.config import settings
    MEMORY_WRITE_ENABLE = getattr(settings, "MEMORY_WRITE_ENABLE", True)
except Exception:
    MEMORY_WRITE_ENABLE = True


class ScheduleItem(BaseModel):
    title: str
    start: str
    end: str
    location: str | None = None


class CandidateItem(BaseModel):
    text: str
    score: float = 0.0
    url: str | None = None


class VerificationInput(BaseModel):
    schedule_items: Union[List[ScheduleItem], str] = Field(
        ..., description="List of schedule items OR a JSON string of such list."
    )
    candidates: Union[List[CandidateItem], str, None] = Field(
        None,
        description="List of candidate knowledge/memory documents OR JSON string, optional but recommended."
    )
    write_memory: bool = Field(
        default=True,
        description="Whether to write schedule summary back to memory."
    )


def safe_parse_list(value):
    """
    确保 value 是 list：
    - 如果是 str，尝试 json.loads
    - 如果是其他类型，返回空列表或抛错
    """
    import json
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return data
            else:
                return []
        except Exception:
            return []
    # 其他类型直接忽略
    return []


def verification_tool_func(schedule_items, candidates=None, write_memory=True):
    evidence_list = []
    notes = []

    # ✅ 1) 安全解析 schedule_items → list of dict
    raw_items = safe_parse_list(schedule_items)

    schedule_objs = []
    for it in raw_items:
        try:
            # 支持 dict 或 ScheduleItem
            if isinstance(it, ScheduleItem):
                schedule_objs.append(it)
            elif isinstance(it, dict):
                schedule_objs.append(ScheduleItem(**it))
            else:
                continue
        except Exception:
            continue

    # ✅ 2) 安全解析 candidates
    raw_cands = safe_parse_list(candidates)

    candidate_objs = []
    for c in raw_cands:
        try:
            if isinstance(c, CandidateItem):
                candidate_objs.append(c)
            elif isinstance(c, dict):
                candidate_objs.append(CandidateItem(**c))
            else:
                continue
        except Exception:
            continue

    # ✅ 3) 构建 evidence （安全）
    for sched in schedule_objs:
        matched = None
        for cand in candidate_objs:
            if sched.title.lower() in (cand.text or "").lower():
                matched = cand
                break
        if matched:
            evidence_list.append({
                "source": matched.url or "mem",
                "snippet": (matched.text or "")[:200],
                "score": float(matched.score),
            })

    notes.append(f"[Verification] evidences={len(evidence_list)}")

    # ✅ 4) 写入记忆（安全）
    memory_written = False
    if write_memory and insert_chunk and schedule_objs:
        try:
            lines = [
                f"{it.title} @ {it.location or 'N/A'} {it.start}-{it.end}"
                for it in schedule_objs
            ]
            memo_text = " | ".join(lines)
            insert_chunk(user_id="u123", kind="memory", text=memo_text)
            memory_written = True
            notes.append("[Verification] wrote episodic memory")
        except Exception as e:
            notes.append(f"[Verification] write memory failed: {e}")

    # ✅ 5) 返回结构化结果，不抛异常
    return {
        "evidence": evidence_list,
        "notes": notes,
        "memory_written": memory_written,
        "checked_items": len(schedule_objs),
        "checked_candidates": len(candidate_objs),
    }



verification_agent_tool = StructuredTool.from_function(
    name="verification_agent_tool",
    description=(
        "Verify schedule items against knowledge/memory candidates. "
        "schedule_items must be a LIST (or JSON string of list). "
        "candidates should also be a LIST (or JSON string or omitted). "
        "Set write_memory=true to store schedule as memory."
    ),
    func=lambda schedule_items, candidates=None, write_memory=True: verification_tool_func(
        schedule_items, candidates, write_memory
    ),
    args_schema=VerificationInput,
)
