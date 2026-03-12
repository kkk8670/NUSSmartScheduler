# app/agent/__init__.py

# LangGraph 服务（唯一对外服务）
from .service import AgentService, PlanReq, PlanRes, CompareReq, CompareRes

# 如需直接构建/复用图，可暴露这两个工厂
from .graph import build_graph
from .graph_compare import build_graph as build_compare_graph

__all__ = [
    "AgentService",
    "PlanReq", "PlanRes",
    "CompareReq", "CompareRes",
    "build_graph", "build_compare_graph",
]
