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


def test_texte_d_accueil():
    at = ouvrir()
    assert at.title[0].value == "Évaluation du programme ACTEE"
    texte = " ".join(m.value for m in at.markdown)
    assert "membre d'une convention ACTEE" in texte and "pré-fléchés" in texte
    assert "la partie 1 est obligatoire" in texte and "la partie 2 est recommandée" in texte


def test_partie2_visible_meme_vide():
    at = ouvrir(structure="S0003")
    # Aperçu : une fiche d'exemple, désactivée, avec les choix visibles.
    assert "aperçu" in at.info[2].value
    assert [p.label for p in at.pills] == ["Travaux réalisés ou en cours", "Montage contractuel"]
    assert all(p.disabled for p in at.pills)
    assert "Brasseurs d'air" in at.pills[0].options
    assert "Lots de travaux proposés" in at.info[1].value
    assert not [b for b in at.button if b.label.startswith("💾 Enregistrer la partie 2")]


def test_partie2_choix_multiples_et_precision(db):
    batiments = core.charger_batiments()
    t = core.tableau_structure(db, "S0001", batiments).assign(statut="Non")
    t.loc[0, "statut"] = OUI_PETITS
    core.enregistrer_reponses(db, "S0001", t, batiments)

    at = ouvrir(structure="S0001")
    travaux, montage = at.pills
    assert not travaux.disabled and len(travaux.options) == 15
    assert not [ti for ti in at.text_input if ti.label.startswith("Précisez")]
    # « Autres travaux » sélectionné : le champ « Précisez » apparaît.
    travaux.set_value(["Ouvrants", "Autres travaux"]).run()
    assert [ti.label for ti in at.text_input if ti.label.startswith("Précisez")] == ["Précisez (autres travaux)"]
    bouton(at, "💾 Enregistrer la partie 2").click().run()
    assert "précisez-le" in at.error[0].value
    next(ti for ti in at.text_input if ti.label.startswith("Précisez")).input("Toiture végétalisée")
    at.pills[1].set_value(["Marché de Partenariat"])
    at.number_input[0].set_value(40)
    bouton(at, "💾 Enregistrer la partie 2").click().run()
    assert not at.exception
    assert "Partie 2 enregistrée" in at.success[0].value
    relu = core.tableau_details(db, "S0001", batiments).iloc[0]
    assert relu["travaux"] == ["Ouvrants", "Autres travaux"]
    assert relu["autres_travaux_precision"] == "Toiture végétalisée"
    assert relu["montage_contractuel"] == ["Marché de Partenariat"]
    assert relu["economie_energie_finale_pct"] == 40
    # Après rechargement, les choix enregistrés sont en surbrillance.
    assert at.pills[0].value == ["Ouvrants", "Autres travaux"]


def test_recherche_sur_l_accueil():
    at = ouvrir()
    at.text_input[0].input("montclair").run()
    assert [b.label for b in at.button][:-1] == ["Ville de Montclair"]


def test_lien_direct_et_cases_a_cocher():
    at = ouvrir(structure="S0004")
    assert not at.exception
    assert at.metric[0].value == "250"
    assert at.title[0].value == "Évaluation du programme ACTEE"
    texte = " ".join(m.value for m in at.markdown)
    assert "membre d'une convention ACTEE" in texte and "la partie 2 est recommandée" in texte
    assert "Questionnaire de **Département de la Haute-Vallée**" in texte
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


def test_reponses_d_une_version_anterieure(db):
    """Réponses enregistrées avec d'anciens libellés et d'anciennes questions : la page
    doit s'afficher (le tableau de la partie 2, vide, ne doit pas planter)."""
    import json
    batiments = core.charger_batiments()
    t = core.tableau_structure(db, "S0002", batiments).assign(statut="Oui, en petits travaux")
    core.enregistrer_reponses(db, "S0002", t, batiments)
    with core._moteur(db).begin() as con:
        from sqlalchemy import text
        con.execute(text("INSERT INTO details VALUES ('S0002', 'S0002-B001', :d, '2026-10-22')"),
                    {"d": json.dumps({"travaux": ["Ouvrants"], "annee_fin_travaux": 2022})})
    at = ouvrir(structure="S0002")
    assert not at.exception
    assert [m.value for m in at.metric][:2] == ["5", "0"]
    assert len(at.pills) == 2
