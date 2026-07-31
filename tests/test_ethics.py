"""
Tests for kalacore/ethics.py – ethical guardrails and content screening.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from kalacore.ethics import check_request, EthicsViolation


class TestCheckRequestLength:
    def test_empty_text_allowed(self):
        result = check_request("")
        assert result == []

    def test_whitespace_only_allowed(self):
        result = check_request("   \n  \t  ")
        assert result == []

    def test_short_text_allowed(self):
        result = check_request("This is a short poem about nature.")
        assert result == []

    def test_text_at_limit_allowed(self):
        from kalacore.ethics import MAX_TEXT_LENGTH
        text = "x" * MAX_TEXT_LENGTH
        result = check_request(text)
        assert not any(v.code == "TEXT_TOO_LONG" for v in result)

    def test_text_exceeding_limit_rejected(self):
        from kalacore.ethics import MAX_TEXT_LENGTH
        text = "x" * (MAX_TEXT_LENGTH + 1)
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "TEXT_TOO_LONG"
        assert "exceeds" in result[0].message


class TestImitationDetection:
    def test_write_like_detected(self):
        result = check_request("Write like Shakespeare")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_sound_like_detected(self):
        result = check_request("Make it sound like Aretha Franklin")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_in_style_of_detected(self):
        result = check_request("Create something in the style of Picasso")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_pretend_to_be_detected(self):
        result = check_request("Pretend to be Mozart")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_imitate_detected(self):
        result = check_request("Imitate Banksy's style")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_replace_detected(self):
        result = check_request("Replace Frida Kahlo's work")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_trigger_not_detected_outside_phrase(self):
        result = check_request("This is a writer who writes in interesting ways")
        assert not any(v.code == "IMITATION_REQUEST" for v in result)

    def test_case_insensitive_detection(self):
        result = check_request("WRITE LIKE Shakespeare")
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"


class TestUnicodeHomoglyphBypass:
    """Tests for Unicode normalization to prevent homoglyph bypasses."""

    def test_cyrillic_homoglyph_detected(self):
        # Cyrillic 'е' (U+0435) instead of Latin 'e' in "write like"
        text = "write lik" + "е" + " Bob"  # U+0435 is Cyrillic 'е'
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_multiple_cyrillic_homoglyphs_detected(self):
        # Multiple Cyrillic homoglyphs: е(U+0435), a(U+0430)
        text = "writ" + "е" + " lik" + "е" + " Van Gogh"
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_zero_width_character_removed(self):
        # Zero-width characters are removed, allowing detection through cleaning
        # "write like" split by zero-width joiner becomes "writelike" → no match
        # But when there's space after, it should work: "write " + ZWJ + "like"
        text = "write " + chr(0x200D) + "like Bob"  # Space before ZWJ
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_zero_width_non_joiner_removed(self):
        # Zero-width non-joiner is removed during normalization
        text = "write " + chr(0x200C) + "like Bob"  # Space before ZWNJ
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_zero_width_space_removed(self):
        # Zero-width space is removed during normalization
        text = "write " + chr(0x200B) + "like Bob"  # Space before ZWSpace
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_combined_homoglyph_and_zwj_bypass_detected(self):
        # Cyrillic + zero-width characters combined
        text = "writ" + "е" + "‍" + " lik" + "е" + " Bob"
        result = check_request(text)
        assert len(result) == 1
        assert result[0].code == "IMITATION_REQUEST"

    def test_normal_text_not_falsely_flagged(self):
        # Normal text without imitation triggers should pass
        result = check_request("This is a poem about the nature of writing.")
        assert not any(v.code == "IMITATION_REQUEST" for v in result)

    def test_similar_but_different_phrase_allowed(self):
        # "writerly" is not "write like"
        result = check_request("A writerly approach to art")
        assert not any(v.code == "IMITATION_REQUEST" for v in result)


class TestMultipleViolations:
    def test_both_length_and_imitation_detected(self):
        from kalacore.ethics import MAX_TEXT_LENGTH
        text = "Write like Shakespeare " * 5000  # Very long + imitation
        result = check_request(text)
        assert len(result) == 2
        codes = {v.code for v in result}
        assert codes == {"TEXT_TOO_LONG", "IMITATION_REQUEST"}
