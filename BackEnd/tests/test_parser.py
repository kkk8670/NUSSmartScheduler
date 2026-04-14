# BackEnd/tests/test_parser.py

"""
two parts

A: Harmonization of the format of time strings

B: Integration test functions are properly mounted on the Pydantic schema
"""

import pytest
from pydantic import ValidationError
 
from app.schemas.tasks import _hhmm_from_any, TaskIn


class TestHhmmFromAny:
    """
    Validation:
    1. Time resolution
    2. Time alignment
    3. Illegal format
    4. illegal values
    """
 
    def test_iso_datetime_parsed(self):
        """
        Verify whether the parsing path can correctly extract time, 
        in case what comes back might be a time string.
        """
        assert _hhmm_from_any("2025-09-01T10:30") == "10:30"
 

    def test_hhmm_with_padding(self):
        """
        Verify the zero-completion logic of regular paths, e.g., single-digit hours (e.g., "9:05") must be zero-completed to "09:05"
        """
        assert _hhmm_from_any("9:05") == "09:05"
 
    def test_invalid_string_raises(self):
        """
        Test error, need to throw ValueError
        """
        with pytest.raises(ValueError):
            _hhmm_from_any("abc")
 
    def test_out_of_range_raises(self):
        """
        Illegal time values must also be intercepted and a ValueError is thrown.
        """
        with pytest.raises(ValueError):
            _hhmm_from_any("25:00")



class TestTaskInValidator:
    """
    TaskIn validator integration

    validator is mounted in two separate places: the earliest/latest field and the prefer_win field. 
    should be test separately.
    """

    def test_taskin_normalizes_earliest_latest(self):
        """
        Validators on earliest and latest must be triggered.
        """
        task = TaskIn(
            id="t1", title="Study", location="COM1",
            earliest="2025-09-01T09:00",
            latest="2025-09-01T12:00",
            duration_min=60,
        )
        assert task.earliest == "09:00"
        assert task.latest   == "12:00"
 
    def test_taskin_prefer_win_normalized(self):
        """
        Validators on validator must be triggered.
        """
        task = TaskIn(
            id="t1", title="Study", location="COM1",
            earliest="09:00", latest="12:00",
            duration_min=60,
            prefer_win=[["2025-09-01T10:00", "2025-09-01T11:00"]],
        )
        assert task.prefer_win == [["10:00", "11:00"]]