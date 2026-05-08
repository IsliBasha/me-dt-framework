"""Tests for quiz navigation buttons — no overlap, correct button per question."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton

_app = QApplication.instance() or QApplication([])


def _make_quiz_page(questions: list[dict]) -> "QuizPage":
    from frontend.pages.quiz import QuizPage
    page = QuizPage()
    page.questions = questions
    page.answers = [None] * len(questions)
    page.current_q = 0
    page._subject = "matematike"
    page._topic = "test"
    import time
    page.start_time = time.time()
    return page


SAMPLE_QUESTIONS = [
    {"question": "1+1?", "options": ["1", "2", "3", "4"], "correct": "2", "explanation": ""},
    {"question": "2+2?", "options": ["2", "3", "4", "5"], "correct": "4", "explanation": ""},
    {"question": "3+3?", "options": ["4", "5", "6", "7"], "correct": "6", "explanation": ""},
]


def _nav_buttons(page) -> list[str]:
    return [b.text() for b in page.findChildren(QPushButton)]


class TestQuizNavigation:
    def test_first_question_shows_next_not_finish(self):
        page = _make_quiz_page(SAMPLE_QUESTIONS)
        page._build_question_ui()
        buttons = _nav_buttons(page)
        assert any("Tjetër" in b for b in buttons), f"Expected Next button, got: {buttons}"
        assert not any("Përfundo" in b for b in buttons), f"Finish should not appear: {buttons}"

    def test_last_question_shows_finish_not_next(self):
        page = _make_quiz_page(SAMPLE_QUESTIONS)
        page.current_q = len(SAMPLE_QUESTIONS) - 1
        page._build_question_ui()
        buttons = _nav_buttons(page)
        assert any("Përfundo" in b for b in buttons), f"Expected Finish button, got: {buttons}"
        assert not any("Tjetër" in b for b in buttons), f"Next should not appear: {buttons}"

    def test_no_duplicate_buttons_after_navigation(self):
        page = _make_quiz_page(SAMPLE_QUESTIONS)
        page._build_question_ui()
        page.current_q = 1
        page._build_question_ui()
        page.current_q = 2
        page._build_question_ui()
        buttons = _nav_buttons(page)
        finish_count = sum(1 for b in buttons if "Përfundo" in b)
        next_count = sum(1 for b in buttons if "Tjetër" in b)
        assert finish_count == 1, f"Expected exactly 1 Finish button, got {finish_count}: {buttons}"
        assert next_count == 0, f"Expected 0 Next buttons, got {next_count}: {buttons}"

    def test_clear_leaves_no_orphaned_buttons(self):
        page = _make_quiz_page(SAMPLE_QUESTIONS)
        page._build_question_ui()
        initial_btn_count = len(page.findChildren(QPushButton))
        page._build_question_ui()
        after_btn_count = len(page.findChildren(QPushButton))
        assert after_btn_count == initial_btn_count, (
            f"Button count grew from {initial_btn_count} to {after_btn_count} — orphaned widgets"
        )
