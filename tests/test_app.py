"""Tests de l'interface avec le testeur intégré de Streamlit (sans navigateur)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from enquete import core


@pytest.fixture(autouse=True)
def base_temporaire(tmp_path, monkeypatch):
    monkeypatch.setenv("ENQUETE_DB", str(tmp_path / "reponses.db"))
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")


def code(id_structure):
    s = core.charger_structures()
    return s.loc[s["id_structure"] == id_structure, "code_acces"].iloc[0]


def ouvrir(**params):
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30)
    for k, v in params.items():
        at.query_params[k] = v
    return at.run()


def test_lien_personnel_affiche_les_batiments_de_la_structure():
    at = ouvrir(code=code("S0004"))
    assert not at.exception
    assert at.title[0].value == "Travaux de rénovation énergétique"
    assert at.metric[0].value == "250"


def test_lien_invalide():
    at = ouvrir(code="FAUX0000")
    assert not at.exception
    assert "pas valide" in at.error[0].value


def test_connexion_email_et_code():
    at = ouvrir()
    at.text_input[0].input("test1@votre-domaine.fr")
    at.text_input[1].input(code("S0001"))
    at.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "4"


def test_validation_refusee_puis_non_partout_puis_validation():
    at = ouvrir(code=code("S0002"))
    boutons = {b.label: b for b in at.button}
    boutons["✅ Valider le questionnaire"].click().run()
    assert "5 bâtiment(s) sans réponse" in at.error[0].value

    boutons = {b.label: b for b in at.button}
    boutons["Mettre « Non » sur les bâtiments non renseignés"].click().run()
    assert not at.exception
    assert at.metric[1].value == "5 / 5"

    boutons = {b.label: b for b in at.button}
    boutons["✅ Valider le questionnaire"].click().run()
    assert at.metric[2].value == "Validé"


def test_admin():
    at = ouvrir(admin="1")
    at.text_input[0].input("mauvais")
    at.button[0].click().run()
    assert "incorrect" in at.error[0].value

    at.text_input[0].input("secret")
    at.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "5"
