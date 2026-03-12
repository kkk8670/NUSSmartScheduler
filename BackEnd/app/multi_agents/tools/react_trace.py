from typing import List, Dict, Any
from langchain.callbacks.base import BaseCallbackHandler

import json

class ReactTraceHandler(BaseCallbackHandler):
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def on_agent_action(self, action, **kwargs):
        # Thought from log
        log = getattr(action, "log", "") or ""
        for line in log.splitlines():
            line = line.strip()
            if line.lower().startswith("thought:"):
                self.steps.append({"type": "thought", "content": line[len("thought:"):].strip()})

        tool_name = getattr(action, "tool", "")
        tool_input = getattr(action, "tool_input", "")
        if isinstance(tool_input, dict):
            try:
                tool_input = json.dumps(tool_input, ensure_ascii=False)
            except Exception:
                tool_input = str(tool_input)

        self.steps.append({
            "type": "action",
            "tool": tool_name,
            "content": str(tool_input)
        })

    def on_tool_end(self, output, **kwargs):
        self.steps.append({
            "type": "observation",
            "content": str(output)
        })

    def on_agent_finish(self, finish, **kwargs):
        log = getattr(finish, "log", "") or ""
        if "Final Answer" in log:
            self.steps.append({
                "type": "final_log",
                "content": log
            })

    def on_tool_start(self, serialized, input_str, **kwargs):
        """
        serialized: {'name': <tool_name>}
        input_str: tool arguments
        """
        tool_name = serialized.get("name", "")
        try:
            _input = input_str if isinstance(input_str, str) else json.dumps(input_str, ensure_ascii=False)
        except Exception:
            _input = str(input_str)

        self.steps.append({
            "type": "action",
            "tool": tool_name,
            "content": _input
        })

    def on_llm_new_token(self, token: str, **kwargs):

        pass
