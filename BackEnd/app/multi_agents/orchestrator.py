# from __future__ import annotations
#
# from .base import State, Message
# from fastapi import Request
# from .dialogue_agent import DialogueAgent
# from .memory_agent import MemoryAgent
# from .knowledge_agent import KnowledgeAgent
# from .reranker_agent import RerankerAgent
# from .scheduling_agent import SchedulingAgent
# from .verification_agent import VerificationAgent
# from ..core.logging import jlog, Timer
#
# PIPELINE = [
#     ("dialogue", DialogueAgent()),
#     ("memory",   MemoryAgent()),
#     ("knowledge",KnowledgeAgent()),
#     ("reranker", RerankerAgent()),
#     ("scheduler",SchedulingAgent()),
#     ("verifier", VerificationAgent()),
# ]
#
# def run_pipeline(request: Request, state: State) -> State:
#     jlog("pipeline_start", trace_id=state.trace_id, state=state.brief())
#     setattr(state, "request", request)
#
#     for name, agent in PIPELINE:
#         t = Timer()
#         # 进入某个 agent 前的摘要（输入）
#         jlog("agent_enter", agent=name, trace_id=state.trace_id, state=state.brief())
#
#         try:
#             state = agent.run(state)
#             ms = t.ms()
#             # 该 agent 结束后的摘要（输出）
#             jlog("agent_exit", agent=name, trace_id=state.trace_id, took_ms=ms, state=state.brief())
#             if not state.ok:
#                 jlog("agent_break", agent=name, trace_id=state.trace_id, reason="state.ok=False")
#                 break
#         except Exception as e:
#             ms = t.ms()
#             jlog("agent_error", agent=name, trace_id=state.trace_id, took_ms=ms, error=str(e))
#             # 你可以选择直接 break，或置 ok=False 再退出
#             state.ok = False
#             break
#
#     jlog("pipeline_end", trace_id=state.trace_id, state=state.brief())
#     return state
#
# def generate_reply(request: Request, state: State) -> str:
#     """
#     Builds a human-readable reply based on the planned tasks and scheduled items.
#     """
#     lines = []
#     if state.plan:
#         lines.append("Plan:")
#         for p in state.plan:
#             lines.append(f"- {p.title}")
#     if state.schedule and state.schedule.items:
#         lines.append("Schedule:")
#         for it in state.schedule.items:
#             lines.append(f"- {it.title}: {it.start}-{it.end} at {it.location}")
#     if state.evidence:
#         lines.append("Evidence:")
#         for ev in state.evidence:
#             lines.append(f"- {ev.source}: {ev.snippet[:50]}… (score={ev.score:.2f})")
#     return "\n".join(lines) if lines else "No plan generated."
