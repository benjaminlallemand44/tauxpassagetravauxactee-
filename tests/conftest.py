import pytest

from enquete import core


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base vide ; ENQUETE_DB pointe dessus pour l'application."""
    chemin = tmp_path / "reponses.db"
    monkeypatch.setenv("ENQUETE_DB", str(chemin))
    yield chemin
    core._moteur_pour.cache_clear()
