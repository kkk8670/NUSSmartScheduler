# BackEnd/tests/test_react_trace.py

"""
Detection guarantees Agent inference layer observability.

The Thought / Action / Observation / Final Answer for each step in the ReAct loop is logged into the self.steps list, which is then exported by jlog to Loki as the only source of data for the observability of the inference chain.

Measure two elements:
A. recording inference steps
B. Handling boundary cases
"""

import pytest
from unittest.mock import MagicMock
from app.multi_agents.tools.react_trace import ReactTraceHandler


# ─── Auxiliary: Construct fake LangChain callback parameters ──────

def make_action(thought_log: str, tool: str, tool_input):
    action = MagicMock()
    action.log = thought_log
    action.tool = tool
    action.tool_input = tool_input
    return action
 
def make_finish(log: str):
    finish = MagicMock()
    finish.log = log
    return finish
 

class TestReactTraceRecording:
    """
    Reasoning Step Record.

    The ReAct loop consists of four steps, Thought, Action, Observation, and Final Answer.
    Each step needs to be captured separately.
    """
    def test_thought_is_captured(self):
        """
        Thought: why make this decision
        Reasoning starts from it, parse from action.log
        """
 
        handler = ReactTraceHandler()
        action = make_action(
            thought_log="Thought: I need to check the schedule\nAction: scheduling_suggest_tool",
            tool="scheduling_suggest_tool",
            tool_input="{}",
        )
        handler.on_agent_action(action)
        thoughts = [s for s in handler.steps if s["type"] == "thought"]
        assert len(thoughts) == 1
        assert "check the schedule" in thoughts[0]["content"]
 
    def test_action_is_captured(self):
        """
        actions: Records the tools called by the Agent and the parameters passed.
        on_agent_action records the tool name and input as a step of type action.
        """

        handler = ReactTraceHandler()
        action = make_action(
            thought_log="",
            tool="memory_agent_tool",
            tool_input="user preferences",
        )
        handler.on_agent_action(action)
        actions = [s for s in handler.steps if s["type"] == "action"]
        assert len(actions) >= 1
        assert any(s["tool"] == "memory_agent_tool" for s in actions)
 
    def test_observation_is_captured(self):
        """
        observation: Records the tool's return value, the result of the tool as seen by the Agent, and the input for the next Thought. 
        Show the reason about the Agent came to a certain conclusion.
        """

        handler = ReactTraceHandler()
        handler.on_tool_end(output="User prefers morning slots")
        observations = [s for s in handler.steps if s["type"] == "observation"]
        assert len(observations) == 1
        assert "morning slots" in observations[0]["content"]
 
    def test_final_answer_is_captured(self):
        """
        Final Answer: on_agent_finish is recorded as final_log when the log contains "Final Answer".
        the end point of the entire reasoning chain, knowing what the Agent has ultimately given.
        """
        handler = ReactTraceHandler()
        finish = make_finish(log='Final Answer: {"reply": "Your schedule is ready"}')
        handler.on_agent_finish(finish)
        finals = [s for s in handler.steps if s["type"] == "final_log"]
        assert len(finals) == 1
        assert "Final Answer" in finals[0]["content"]



class TestReactTraceBoundary:
    """
    Boundary case handling
    A. input serialization case
    B. log empty case
    """
 
    def test_dict_tool_input_serialized(self):
        """
        tool_input needs to be serialized with json.dumps.
        """

        handler = ReactTraceHandler()
        action = make_action(
            thought_log="",
            tool="scheduling_suggest_tool",
            tool_input={"tasks": ["Study", "Lunch"], "mode": "travel"},
        )
        handler.on_agent_action(action)
        actions = [s for s in handler.steps if s["type"] == "action"]
        assert len(actions) >= 1
        # content must be a string, not a dict
        assert isinstance(actions[-1]["content"], str)
 
    def test_empty_log_does_not_crash(self):
        """
        The handler cannot throw an exception if action.log is an empty string or None.
        """
        handler = ReactTraceHandler()
        action = make_action(thought_log="", tool="some_tool", tool_input="")
        try:
            handler.on_agent_action(action)
        except Exception as e:
            pytest.fail(f"on_agent_action raised an exception on empty log: {e}")
