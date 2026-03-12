import json, logging, os, sys, time
from typing import Any, Dict

def setup_logging():
    level = os.getenv("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        stream=sys.stdout,
        format="%(message)s",  # 我们直接输出 JSON
    )

def jlog(event: str, **fields: Dict[str, Any]):
    """
    统一的 JSON 日志。使用方式：
      jlog("agent_start", agent="scheduler", trace_id=..., ...)
    """
    rec = {"event": event, **fields}
    logging.getLogger("multi").info(json.dumps(rec, ensure_ascii=False))

class Timer:
    def __init__(self):
        self.t0 = time.perf_counter()
    def ms(self) -> int:
        return int((time.perf_counter() - self.t0) * 1000)
