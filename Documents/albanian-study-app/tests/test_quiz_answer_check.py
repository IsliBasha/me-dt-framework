"""Tests for quiz answer normalization — correct field must be full option text."""
import pytest
from backend.api.quiz import normalize_correct_answer


class TestNormalizeCorrectAnswer:
    def test_letter_a_maps_to_first_option(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("A", options) == "20"

    def test_letter_b_maps_to_second_option(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("B", options) == "25"

    def test_letter_c_maps_to_third_option(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("C", options) == "30"

    def test_letter_d_maps_to_fourth_option(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("D", options) == "35"

    def test_lowercase_letter_also_works(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("b", options) == "25"

    def test_full_option_text_unchanged(self):
        options = ["20", "25", "30", "35"]
        assert normalize_correct_answer("25", options) == "25"

    def test_numeric_string_unchanged(self):
        options = ["x=2", "x=4", "x=6", "x=8"]
        assert normalize_correct_answer("x=4", options) == "x=4"

    def test_letter_out_of_range_returns_original(self):
        options = ["A", "B"]
        assert normalize_correct_answer("D", options) == "D"

    def test_empty_options_returns_original(self):
        assert normalize_correct_answer("A", []) == "A"

    def test_empty_correct_returns_empty(self):
        assert normalize_correct_answer("", ["X", "Y"]) == ""
