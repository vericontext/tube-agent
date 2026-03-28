"""Tests for pipeline utility functions."""

from tube_agent.services.pipeline import parse_duration, format_number


class TestParseDuration:
    def test_hours_minutes_seconds(self):
        assert parse_duration("PT1H2M3S") == 3723

    def test_minutes_only(self):
        assert parse_duration("PT15M") == 900

    def test_seconds_only(self):
        assert parse_duration("PT30S") == 30

    def test_hours_only(self):
        assert parse_duration("PT2H") == 7200

    def test_hours_and_seconds(self):
        assert parse_duration("PT1H30S") == 3630

    def test_empty(self):
        assert parse_duration("") == 0

    def test_none(self):
        assert parse_duration(None) == 0

    def test_invalid(self):
        assert parse_duration("invalid") == 0


class TestFormatNumber:
    def test_millions(self):
        assert format_number(1500000) == "1.5M"

    def test_thousands(self):
        assert format_number(2500) == "2.5K"

    def test_small(self):
        assert format_number(999) == "999"

    def test_exact_million(self):
        assert format_number(1000000) == "1.0M"

    def test_exact_thousand(self):
        assert format_number(1000) == "1.0K"

    def test_zero(self):
        assert format_number(0) == "0"
