"""Compose config must keep auth SQLite off the ephemeral container FS."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def test_backend_sets_persistent_kala_db_path():
    assert "KALA_DB_PATH=" in COMPOSE
    assert "/data/kalaos.db" in COMPOSE


def test_backend_mounts_data_volume():
    assert "backend_data:/data" in COMPOSE
    assert "backend_data:" in COMPOSE.split("volumes:")[-1]
