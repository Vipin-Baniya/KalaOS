"""
Tests for Music Studio Phase — AI Beat Generator endpoint and function.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from main import app
from kalacore.kalaproducer import generate_ai_beat

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit: generate_ai_beat
# ---------------------------------------------------------------------------

class TestGenerateAiBeat:
    def test_returns_dict(self):
        result = generate_ai_beat("lofi chill beat")
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = generate_ai_beat("trap beat")
        for k in ["bpm", "drums", "melody", "genre", "prompt"]:
            assert k in result, f"Missing key: {k}"

    def test_bpm_is_positive_int(self):
        result = generate_ai_beat("house music")
        assert isinstance(result["bpm"], int)
        assert 40 <= result["bpm"] <= 300

    def test_drums_has_all_rows(self):
        result = generate_ai_beat("hip-hop beat")
        for row in ["kick", "snare", "hihat", "openhat", "clap", "perc"]:
            assert row in result["drums"], f"Missing drum row: {row}"

    def test_drums_16_steps(self):
        result = generate_ai_beat("lofi chill")
        for row, pattern in result["drums"].items():
            assert len(pattern) == 16, f"Row {row} should have 16 steps"

    def test_drums_binary_values(self):
        result = generate_ai_beat("trap")
        for row, pattern in result["drums"].items():
            for v in pattern:
                assert v in (0, 1), f"Row {row} has non-binary value: {v}"

    def test_melody_is_list_of_strings(self):
        result = generate_ai_beat("jazz swing")
        assert isinstance(result["melody"], list)
        assert len(result["melody"]) >= 1
        for note in result["melody"]:
            assert isinstance(note, str)

    def test_genre_is_string(self):
        result = generate_ai_beat("house beat")
        assert isinstance(result["genre"], str)

    def test_prompt_is_echoed(self):
        result = generate_ai_beat("lofi chill beat")
        assert result["prompt"] == "lofi chill beat"

    def test_lofi_genre_detected(self):
        result = generate_ai_beat("lofi hip hop beats to study to")
        assert result["genre"] == "lofi"

    def test_trap_genre_detected(self):
        result = generate_ai_beat("trap hard 808")
        assert result["genre"] == "trap"

    def test_house_genre_detected(self):
        result = generate_ai_beat("deep house party")
        assert result["genre"] == "house"

    def test_default_genre_fallback(self):
        result = generate_ai_beat("unknown genre xyz")
        assert result["genre"] == "default"
        assert 40 <= result["bpm"] <= 300

    def test_explicit_bpm_override(self):
        result = generate_ai_beat("trap beat 160bpm")
        assert result["bpm"] == 160

    def test_explicit_bpm_with_space(self):
        result = generate_ai_beat("lofi beat 75 bpm")
        assert result["bpm"] == 75

    def test_bpm_clamped_to_max(self):
        # 400 is out of range, should stay at profile default
        result = generate_ai_beat("trap beat 400bpm")
        assert result["bpm"] <= 300

    def test_mood_affects_bpm(self):
        base = generate_ai_beat("pop")
        fast = generate_ai_beat("pop fast")
        assert fast["bpm"] > base["bpm"]

    def test_dnb_detected(self):
        result = generate_ai_beat("drum and bass dnb jungle")
        assert result["genre"] == "dnb"

    def test_afrobeats_detected(self):
        result = generate_ai_beat("afrobeats summer vibes")
        assert result["genre"] == "afrobeats"

    def test_reggaeton_detected(self):
        result = generate_ai_beat("reggaeton dembow")
        assert result["genre"] == "reggaeton"

    def test_ambient_detected(self):
        result = generate_ai_beat("ambient drone meditation")
        assert result["genre"] == "ambient"

    def test_empty_prompt_returns_default(self):
        # The function itself doesn't raise - it returns the default profile.
        # Validation happens at the API layer.
        result = generate_ai_beat("")
        assert isinstance(result, dict)
        assert "bpm" in result

    def test_whitespace_prompt_still_returns(self):
        # generate_ai_beat does not strip – whitespace becomes default
        result = generate_ai_beat("   ")
        assert isinstance(result, dict)

    def test_all_genres_return_valid_result(self):
        genres = [
            "lofi", "trap", "hip-hop", "house", "techno", "reggaeton",
            "dnb", "jazz", "pop", "afrobeats", "ambient", "drill",
            "funk", "soul", "chill",
        ]
        for genre in genres:
            result = generate_ai_beat(genre)
            assert result["bpm"] >= 40
            assert len(result["drums"]["kick"]) == 16


# ---------------------------------------------------------------------------
# Integration: POST /music-studio/ai-beat
# ---------------------------------------------------------------------------

class TestAiBeatEndpoint:
    def test_basic_request(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "lofi chill beat"})
        assert resp.status_code == 200

    def test_response_has_required_fields(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "trap hard"})
        assert resp.status_code == 200
        data = resp.json()
        for k in ["bpm", "drums", "melody", "genre", "prompt"]:
            assert k in data, f"Missing field: {k}"

    def test_bpm_in_valid_range(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "house music"})
        assert resp.status_code == 200
        assert 40 <= resp.json()["bpm"] <= 300

    def test_drums_all_rows_present(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "hip-hop boom bap"})
        assert resp.status_code == 200
        drums = resp.json()["drums"]
        for row in ["kick", "snare", "hihat", "openhat", "clap", "perc"]:
            assert row in drums

    def test_drums_16_steps(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "techno rave"})
        assert resp.status_code == 200
        for row, pattern in resp.json()["drums"].items():
            assert len(pattern) == 16

    def test_melody_is_list(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "jazz"})
        assert resp.status_code == 200
        assert isinstance(resp.json()["melody"], list)

    def test_empty_prompt_returns_422(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": ""})
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self):
        resp = client.post("/music-studio/ai-beat", json={})
        assert resp.status_code == 422

    def test_whitespace_prompt_returns_422(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "   "})
        assert resp.status_code == 422

    def test_explicit_bpm_in_prompt(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "lofi beat 75bpm"})
        assert resp.status_code == 200
        assert resp.json()["bpm"] == 75

    def test_lofi_detected(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "lofi chill"})
        assert resp.status_code == 200
        assert resp.json()["genre"] == "lofi"

    def test_trap_detected(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "trap banger"})
        assert resp.status_code == 200
        assert resp.json()["genre"] == "trap"

    def test_prompt_echoed_in_response(self):
        resp = client.post("/music-studio/ai-beat", json={"prompt": "afrobeats summer"})
        assert resp.status_code == 200
        assert resp.json()["prompt"] == "afrobeats summer"

    def test_various_genres(self):
        prompts = [
            "house music", "techno club", "dnb jungle",
            "jazz swing", "pop mainstream", "afrobeats",
        ]
        for p in prompts:
            resp = client.post("/music-studio/ai-beat", json={"prompt": p})
            assert resp.status_code == 200, f"Failed for prompt: {p}"


# ---------------------------------------------------------------------------
# Unit: generate_sampler_bank
# ---------------------------------------------------------------------------

from kalacore.kalaproducer import generate_sampler_bank, generate_virtual_keyboard_config


class TestGenerateSamplerBankUnit:
    def test_drums_bank_returns_16_pads(self):
        result = generate_sampler_bank("drums")
        assert result["pad_count"] == 16
        assert len(result["pads"]) == 16

    def test_drums_bank_field(self):
        result = generate_sampler_bank("drums")
        assert result["bank"] == "drums"

    def test_first_drum_pad_is_kick(self):
        result = generate_sampler_bank("drums")
        assert result["pads"][0]["label"] == "Kick"

    def test_pad_has_required_fields(self):
        result = generate_sampler_bank("drums")
        pad = result["pads"][0]
        assert "index" in pad
        assert "label" in pad
        assert "sample_url" in pad
        assert "velocity" in pad
        assert "pitch" in pad

    def test_sample_url_format(self):
        result = generate_sampler_bank("drums")
        assert result["pads"][0]["sample_url"].startswith("https://cdn.kalaos.com/samples/drums/")
        assert result["pads"][0]["sample_url"].endswith(".wav")

    def test_invalid_bank_raises_value_error(self):
        with pytest.raises(ValueError):
            generate_sampler_bank("invalid_bank")

    def test_custom_pad_count(self):
        result = generate_sampler_bank("drums", pad_count=8)
        assert result["pad_count"] == 8
        assert len(result["pads"]) == 8

    def test_all_banks_return_pads(self):
        for bank in ["drums", "percussion", "bass", "synth", "vocals", "fx"]:
            result = generate_sampler_bank(bank)
            assert len(result["pads"]) == 16, f"Bank {bank} did not return 16 pads"

    def test_percussion_first_pad(self):
        result = generate_sampler_bank("percussion")
        assert result["pads"][0]["label"] == "Clave"

    def test_pad_indices_sequential(self):
        result = generate_sampler_bank("drums")
        for i, pad in enumerate(result["pads"]):
            assert pad["index"] == i

    def test_pad_velocity_default_100(self):
        result = generate_sampler_bank("drums")
        for pad in result["pads"]:
            assert pad["velocity"] == 100


# ---------------------------------------------------------------------------
# Unit: generate_virtual_keyboard_config
# ---------------------------------------------------------------------------

class TestGenerateVirtualKeyboardConfigUnit:
    def test_piano_returns_12_notes(self):
        result = generate_virtual_keyboard_config("piano")
        assert len(result["notes"]) == 12

    def test_piano_waveform_is_triangle(self):
        result = generate_virtual_keyboard_config("piano")
        assert result["waveform"] == "triangle"

    def test_organ_waveform_is_square(self):
        result = generate_virtual_keyboard_config("organ")
        assert result["waveform"] == "square"

    def test_strings_waveform_is_sawtooth(self):
        result = generate_virtual_keyboard_config("strings")
        assert result["waveform"] == "sawtooth"

    def test_instrument_echoed(self):
        result = generate_virtual_keyboard_config("synth")
        assert result["instrument"] == "synth"

    def test_octave_echoed(self):
        result = generate_virtual_keyboard_config("piano", octave=5)
        assert result["octave"] == 5

    def test_effects_present(self):
        result = generate_virtual_keyboard_config("piano")
        assert "effects" in result
        assert result["effects"]["reverb"] == 20
        assert result["effects"]["volume"] == 80

    def test_first_note_is_c(self):
        result = generate_virtual_keyboard_config("piano")
        assert result["notes"][0]["note"] == "C"

    def test_a4_frequency(self):
        result = generate_virtual_keyboard_config("piano", octave=4)
        a_note = next(n for n in result["notes"] if n["note"] == "A")
        assert a_note["frequency"] == 440.0

    def test_invalid_instrument_raises_value_error(self):
        with pytest.raises(ValueError):
            generate_virtual_keyboard_config("trumpet")


# ---------------------------------------------------------------------------
# API: POST /music-studio/sampler-bank
# ---------------------------------------------------------------------------

class TestSamplerBankEndpoint:
    def test_drums_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "drums"})
        assert resp.status_code == 200

    def test_percussion_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "percussion"})
        assert resp.status_code == 200

    def test_bass_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "bass"})
        assert resp.status_code == 200

    def test_synth_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "synth"})
        assert resp.status_code == 200

    def test_vocals_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "vocals"})
        assert resp.status_code == 200

    def test_fx_bank_200(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "fx"})
        assert resp.status_code == 200

    def test_invalid_bank_returns_422(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "invalid"})
        assert resp.status_code == 422

    def test_missing_bank_returns_422(self):
        resp = client.post("/music-studio/sampler-bank", json={})
        assert resp.status_code == 422

    def test_response_has_pads(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "drums"})
        assert resp.status_code == 200
        data = resp.json()
        assert "pads" in data
        assert len(data["pads"]) == 16

    def test_custom_pad_count(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "drums", "pad_count": 8})
        assert resp.status_code == 200
        assert resp.json()["pad_count"] == 8

    def test_response_bank_field(self):
        resp = client.post("/music-studio/sampler-bank", json={"bank": "fx"})
        assert resp.json()["bank"] == "fx"


# ---------------------------------------------------------------------------
# API: POST /music-studio/keyboard-config
# ---------------------------------------------------------------------------

class TestKeyboardConfigEndpoint:
    def test_piano_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano"})
        assert resp.status_code == 200

    def test_organ_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "organ"})
        assert resp.status_code == 200

    def test_strings_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "strings"})
        assert resp.status_code == 200

    def test_synth_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "synth"})
        assert resp.status_code == 200

    def test_bass_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "bass"})
        assert resp.status_code == 200

    def test_marimba_200(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "marimba"})
        assert resp.status_code == 200

    def test_invalid_instrument_returns_422(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "trumpet"})
        assert resp.status_code == 422

    def test_missing_instrument_returns_422(self):
        resp = client.post("/music-studio/keyboard-config", json={})
        assert resp.status_code == 422

    def test_octave_below_range_returns_422(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano", "octave": 0})
        assert resp.status_code == 422

    def test_octave_above_range_returns_422(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano", "octave": 9})
        assert resp.status_code == 422

    def test_response_has_notes(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano"})
        assert resp.status_code == 200
        data = resp.json()
        assert "notes" in data
        assert len(data["notes"]) == 12

    def test_response_has_waveform(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano"})
        assert resp.json()["waveform"] == "triangle"

    def test_response_has_effects(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano"})
        assert "effects" in resp.json()

    def test_custom_octave(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "piano", "octave": 3})
        assert resp.status_code == 200
        assert resp.json()["octave"] == 3

    def test_marimba_waveform_is_sine(self):
        resp = client.post("/music-studio/keyboard-config", json={"instrument": "marimba"})
        assert resp.json()["waveform"] == "sine"
