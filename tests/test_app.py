"""Tests de l'interface avec le testeur intégré de Streamlit (sans navigateur)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from enquete import core
from enquete.questionnaire import OUI_PETITS


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


def bouton(at, debut):
    return next(b for b in at.button if b.label.startswith(debut))


def test_lien_personnel_affiche_les_batiments_de_la_structure():
    at = ouvrir(code=code("S0004"))
    assert not at.exception
    assert at.title[0].value == "Travaux de rénovation énergétique"
    assert at.metric[0].value == "250"
    assert "petits travaux" in at.info[0].value.lower()


def test_lien_invalide():
    at = ouvrir(code="FAUX0000")
    assert not at.exception
    assert "pas valide" in at.error[0].value


def test_connexion_second_contact_meme_code():
    at = ouvrir()
    at.text_input[0].input("test3-bis@votre-domaine.fr")
    at.text_input[1].input(code("S0003"))
    at.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "80"


def test_parcours_complet():
    at = ouvrir(code=code("S0002"))
    bouton(at, "✅ Valider").click().run()
    assert "sans réponse" in at.error[0].value

    bouton(at, "Mettre « Non »").click().run()
    assert not at.exception
    assert at.metric[1].value == "5 / 5"

    bouton(at, "✅ Valider").click().run()
    assert not at.exception
    assert at.metric[2].value == "Validé"


def test_validation_bloquee_par_partie2_obligatoire():
    db = Path(core.chemin_base())
    batiments = core.charger_batiments()
    t = core.tableau_structure(db, "S0001", batiments).assign(statut="Non")
    t.loc[0, "statut"] = OUI_PETITS
    core.enregistrer_reponses(db, "S0001", t, batiments)

    at = ouvrir(code=code("S0001"))
    assert "(1 bâtiment(s))" in at.tabs[1].label
    bouton(at, "✅ Valider").click().run()
    assert not at.exception
    assert "Partie 2 à compléter" in at.error[0].value
    assert at.metric[2].value == "En cours de saisie"


def test_admin():
    at = ouvrir(admin="1")
    at.text_input[0].input("mauvais")
    at.button[0].click().run()
    assert "incorrect" in at.error[0].value

    at.text_input[0].input("secret")
    at.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "5"
