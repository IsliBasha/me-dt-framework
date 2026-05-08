"""Unit tests for flashcard text formatting."""
import pytest
from frontend.pages.flashcards import _format_card_text, _calc_font_size


class TestFormatCardText:
    def test_newline_becomes_br(self):
        result = _format_card_text("Hapi 1\nHapi 2\nHapi 3")
        assert "<br>" in result
        assert "\n" not in result

    def test_subscript_digits_converted(self):
        # ₀₁₂₃ are Unicode subscript digits U+2080–U+2083
        result = _format_card_text("t₁ + t₂ = t₀")
        assert "₀" not in result
        assert "₁" not in result
        assert "₂" not in result
        assert "<sub>1</sub>" in result
        assert "<sub>2</sub>" in result
        assert "<sub>0</sub>" in result

    def test_superscript_digits_converted(self):
        # ² ³ are U+00B2 U+00B3 (common superscripts)
        result = _format_card_text("v₀² / 2g = h")
        assert "²" not in result
        assert "<sup>2</sup>" in result

    def test_plain_text_unchanged(self):
        text = "Çfarë është koha mesore?"
        result = _format_card_text(text)
        assert "Çfarë" in result
        assert "koha mesore" in result

    def test_empty_string(self):
        assert _format_card_text("") == ""

    def test_multiple_newlines(self):
        result = _format_card_text("A\nB\nC\nD")
        assert result.count("<br>") == 3

    def test_mixed_content(self):
        text = "Formula: h = v₀²/(2g)\nKu g = 10 m/s²"
        result = _format_card_text(text)
        assert "<br>" in result
        assert "₀" not in result
        assert "²" not in result


class TestCalcFontSize:
    def test_short_text_gets_max_size(self):
        assert _calc_font_size(30) == 16

    def test_medium_text_shrinks(self):
        size = _calc_font_size(150)
        assert size < 16
        assert size >= 10

    def test_long_text_shrinks_more(self):
        assert _calc_font_size(150) > _calc_font_size(300)

    def test_very_long_text_hits_floor(self):
        assert _calc_font_size(9999) >= 9

    def test_empty_text_gets_max_size(self):
        assert _calc_font_size(0) == 16

    def test_monotonically_decreasing(self):
        sizes = [_calc_font_size(n) for n in [0, 80, 160, 240, 320, 400]]
        for a, b in zip(sizes, sizes[1:]):
            assert a >= b
