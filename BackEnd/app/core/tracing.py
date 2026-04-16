from __future__ import annotations
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False

def init_langfuse() -> bool:
    """
    全局初始化 Langfuse（v3 模式：只需调用一次 Langfuse() 构造器，
    之后所有地方用 get_client() 取单例）。
    返回 True 表示初始化成功，False 表示未配置或失败。
    """
    global _initialized
    if _initialized:
        return True

    pk = settings.LANGFUSE_PUBLIC_KEY
    sk = settings.LANGFUSE_SECRET_KEY
    host = settings.LANGFUSE_HOST

    if not pk or not sk:
        logger.info("Langfuse not configured (keys missing). Tracing disabled.")
        _initialized = True   # 标记已尝试，避免重复打印日志
        return False

    try:
        from langfuse import Langfuse
        # v3：构造一次即注册全局 OTel 追踪器，get_client() 之后随处可用
        Langfuse(public_key=pk, secret_key=sk, host=host)
        _initialized = True
        logger.info("Langfuse tracing enabled → %s", host)
        return True
    except Exception as e:
        logger.warning("Langfuse init failed: %s. Tracing disabled.", e)
        _initialized = True
        return False


def get_langfuse():
    """
    返回全局 Langfuse client（v3 单例），未配置时返回 None。
    """
    if not init_langfuse():
        return None
    try:
        from langfuse import get_client
        return get_client()
    except Exception:
        return None


def make_lc_handler(
    *,
    trace_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    返回 LangChain CallbackHandler 列表，供 .invoke(config={"callbacks": [...]}) 使用。
    v3 中 import 路径从 langfuse.callback 改为 langfuse.langchain。
    """
    if get_langfuse() is None:
        return []
    try:
        from langfuse.langchain import CallbackHandler   # ← v3 新路径
        handler = CallbackHandler(
            trace_name=trace_name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )
        return [handler]
    except Exception as e:
        logger.warning("Failed to create Langfuse CallbackHandler: %s", e)
        return []


def flush():
    """在 FastAPI lifespan shutdown 时调用，确保缓冲区数据上报。"""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
        except Exception as e:
            logger.warning("Langfuse flush failed: %s", e)