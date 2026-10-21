"""Base de test : SQLite toujours ; PostgreSQL en plus si TEST_DATABASE_URL est défini,
par exemple TEST_DATABASE_URL=postgresql://postgres@localhost:55432/postgres"""
import os

import pytest
from sqlalchemy import text

from enquete import core

BASES = ["sqlite"] + (["postgresql"] if os.environ.get("TEST_DATABASE_URL") else [])


@pytest.fixture(params=BASES)
def db(request, tmp_path, monkeypatch):
    """Base vide ; DATABASE_URL / ENQUETE_DB pointent dessus pour l'application."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    core._moteur_pour.cache_clear()
    if request.param == "sqlite":
        chemin = tmp_path / "reponses.db"
        monkeypatch.setenv("ENQUETE_DB", str(chemin))
        yield chemin
    else:
        url = os.environ["TEST_DATABASE_URL"]
        with core._moteur_pour(url).begin() as con:
            con.execute(text("DROP TABLE IF EXISTS reponses, details, validations"))
        core._moteur_pour(url).dispose()
        core._moteur_pour.cache_clear()
        monkeypatch.setenv("DATABASE_URL", url)
        yield url
    core._moteur_pour.cache_clear()
