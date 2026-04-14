# BackEnd/tests/test_api.py

"""
Router for two things:
    A. Input validation: Illegal input is intercepted before it enters the business logic
    B. Response structure: normal input returns a fixed structure that the front-end depends on
"""
 

import pytest
from unittest.mock import patch, MagicMock



class TestPlannerValidation:
    """
    Parameter input verification
    1. Empty tasks
    2. Time window constraint
    """
 
    def test_empty_tasks_returns_400(self, client):
        """
        tasks must return 400 if it is empty, you cannot pass an empty list to solver.
        """
 
        resp = client.post("/api/planner/generate", json={
            "tasks": [],
            "commuteMode": "auto"
        })
        assert resp.status_code == 400
 
    def test_invalid_time_window_returns_400(self, client):
        """
        Tasks with earliest > latest must return 400
        """ 
         
        resp = client.post("/api/planner/generate", json={
            "tasks": [{
                "id": "t1",
                "title": "Study",
                "location": "COM1",
                "earliest": "12:00",
                "latest": "09:00",   # ***
                "duration_min": 60,
                "fixed": False,
                "priority": 2,
            }],
            "commuteMode": "auto"
        })
        assert resp.status_code == 400
 
 
 
class TestPlannerResponse:
    """
    test for:
    1. status code
    2. field structure
    """

    # mock off travel_graph and solver to make this test focus only on routing layer behavior
    @patch("app.routers.planner.load_travel_graph", return_value=MagicMock())
    @patch("app.routers.planner.solve_plan", return_value=[
        {"id": "t1", "title": "Study", "loc": "COM1", "start": "09:00", "end": "10:00"}
    ])
    def test_valid_request_returns_200(self, mock_solve, mock_graph, client):
        """
        Normal input interface returns 200
        """
        resp = client.post("/api/planner/generate", json={
            "tasks": [{
                "id": "t1",
                "title": "Study",
                "location": "COM1",
                "earliest": "09:00",
                "latest": "12:00",
                "duration_min": 60,
                "fixed": False,
                "priority": 2,
            }],
            "commuteMode": "auto"
        })
        assert resp.status_code == 200
 
    @patch("app.routers.planner.load_travel_graph", return_value=MagicMock())
    @patch("app.routers.planner.solve_plan", return_value=[
        {"id": "t1", "title": "Study", "loc": "COM1", "start": "09:00", "end": "10:00"}
    ])
    def test_response_has_required_keys(self, mock_solve, mock_graph, client):
        """
        response mush include: ok / plans / all_timelines
        """
        resp = client.post("/api/planner/generate", json={
            "tasks": [{
                "id": "t1",
                "title": "Study",
                "location": "COM1",
                "earliest": "09:00",
                "latest": "12:00",
                "duration_min": 60,
                "fixed": False,
                "priority": 2,
            }],
            "commuteMode": "auto"
        })
        body = resp.json()
        assert "ok"            in body
        assert "plans"         in body
        assert "all_timelines" in body