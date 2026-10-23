"""Tests de l'interface avec le testeur intégré de Streamlit (sans navigateur)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from enquete import core
from enquete.questionnaire import OUI_PETITS


@pytest.fixture(autouse=True)
def base_temporaire(db, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)


def ouvrir(**params):
    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30)
    for k, v in params.items():
        at.query_params[k] = v
    return at.run()


def bouton(at, debut):
    return next(b for b in at.button if b.label.startswith(debut))


def test_accueil_liste_les_collectivites_et_ouvre_la_bonne():
    at = ouvrir()
    assert not at.exception
    noms = [b.label for b in at.button]
    assert "Département de la Haute-Vallée" in noms and len(noms) == 6  # 5 + administration
    bouton(at, "Département de la Haute-Vallée").click().run()
    assert not at.exception
    assert at.query_params["structure"] in ("S0004", ["S0004"])
    assert at.metric[0].value == "250"


def test_recherche_sur_l_accueil():
    at = ouvrir()
    at.text_input[0].input("montclair").run()
    assert [b.label for b in at.button][:-1] == ["Ville de Montclair"]


def test_lien_direct_et_cases_a_cocher():
    at = ouvrir(structure="S0004")
    assert not at.exception
    assert at.metric[0].value == "250"
    assert at.title[0].value == "Enquête d'impact Travaux"
    assert "Consigne" in at.info[0].value and "Travaux prévus" in at.info[0].value
    assert [t.label for t in at.tabs] == ["Partie 1 : État des bâtiments", "Partie 2 : Détails des travaux"]
    tableau = at.get("dataframe")[0].value
    assert "rn" not in tableau.columns and "code_postal" not in tableau.columns  # masqués
    assert [c for c in tableau.columns if c.startswith("rep_")] == [f"rep_{i}" for i in range(5)]
    # Les colonnes descriptives viennent avant les cases à cocher.
    assert list(tableau.columns).index("typologie") < list(tableau.columns).index("rep_0")


def test_collectivite_inconnue():
    at = ouvrir(structure="S9999")
    assert not at.exception
    assert "introuvable" in at.error[0].value


def test_parcours_complet():
    at = ouvrir(structure="S0002")
    bouton(at, "✅ Valider").click().run()
    assert "sans réponse" in at.error[0].value

    bouton(at, "Cocher « Non »").click().run()
    assert not at.exception
    assert "coché pour" in at.success[0].value

    bouton(at, "✅ Valider").click().run()
    assert not at.exception
    assert at.metric[2].value == "Validé"


def test_partie2_recommandee_validation_possible(db):
    batiments = core.charger_batiments()
    t = core.tableau_structure(db, "S0001", batiments).assign(statut="Non")
    t.loc[0, "statut"] = OUI_PETITS
    core.enregistrer_reponses(db, "S0001", t, batiments)

    at = ouvrir(structure="S0001")
    assert at.metric[1].value == "1"
    assert "énergie finale" in at.info[1].value
    assert "Difficultés rencontrées" in at.warning[0].value
    bouton(at, "✅ Valider").click().run()
    assert not at.exception
    assert at.metric[2].value == "Validé"
    assert "recommandée" in at.success[0].value


def test_admin_ouverte_sans_mot_de_passe():
    at = ouvrir(admin="1")
    assert not at.exception
    assert at.metric[0].value == "5"


def test_admin_protegee_si_mot_de_passe(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    at = ouvrir(admin="1")
    at.text_input[0].input("mauvais")
    bouton(at, "Se connecter").click().run()
    assert "incorrect" in at.error[0].value
    at.text_input[0].input("secret")
    bouton(at, "Se connecter").click().run()
    assert not at.exception
    assert at.metric[0].value == "5"


def test_moe_precoche_oui_grands_travaux():
    at = ouvrir(structure="S0004")
    tableau = at.get("dataframe")[0].value
    moe = tableau["financements"].str.contains("MOE")
    assert moe.any() and (~moe).any()
    # « Oui, grands travaux » (rep_1) pré-coché pour chaque bâtiment avec MOE, et seulement eux.
    assert tableau.loc[moe, "rep_1"].all()
    assert not tableau.loc[~moe, ["rep_0", "rep_1", "rep_2", "rep_3", "rep_4"]].any().any()
    assert "pré-cochée" in " ".join(c.value for c in at.caption)
