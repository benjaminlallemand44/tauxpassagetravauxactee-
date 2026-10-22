import pandas as pd
import pytest

from enquete import core
from enquete.questionnaire import OUI_GRANDS, OUI_PETITS, STATUT_SI_MOE
from preparer_donnees import format_brevo, preparer


@pytest.fixture
def ref():
    return core.charger_structures(), core.charger_batiments()


def test_referentiel_de_test(ref):
    structures, batiments = ref
    tailles = batiments.groupby("id_structure").size().to_dict()
    assert tailles == {"S0001": 4, "S0002": 5, "S0003": 80, "S0004": 250, "S0005": 100}
    assert structures["id_structure"].is_unique
    # RN masqué au répondant (mais conservé dans le référentiel et l'export).
    assert core.colonnes_affichees(batiments) == [
        "num", "nom_batiment", "adresse", "code_postal", "commune", "typologie", "financements"]
    assert "rn" in batiments.columns


def test_detection_moe():
    assert core.a_recu_moe(pd.Series({"financements": "Audit + MOE"}))
    assert core.a_recu_moe(pd.Series({"financements": "maîtrise d'œuvre"}))
    assert core.a_recu_moe(pd.Series({"moe": "Oui"}))
    assert not core.a_recu_moe(pd.Series({"financements": "Audit + AMO"}))
    assert not core.a_recu_moe(pd.Series({"financements": "MOEX"}))


def test_preselection_moe(ref, db):
    _, batiments = ref
    t = core.tableau_structure(db, "S0004", batiments)
    moe = t["financements"].str.contains("MOE")
    assert moe.any() and (~moe).any()
    assert (t.loc[moe, "statut"] == STATUT_SI_MOE).all()
    assert t.loc[moe, "pre_rempli"].all()
    assert (t.loc[~moe, "statut"] == "").all()

    # Une fois la réponse enregistrée (même modifiée), la pré-sélection ne s'applique plus.
    i = t.index[moe][0]
    t.loc[i, "statut"] = "Non"
    core.enregistrer_reponses(db, "S0004", t.loc[[i]], batiments)
    relu = core.tableau_structure(db, "S0004", batiments)
    assert relu.loc[i, "statut"] == "Non"
    assert not relu.loc[i, "pre_rempli"]


def test_tableau_ne_contient_que_les_batiments_de_la_structure(ref, db):
    _, batiments = ref
    for id_s, n in [("S0001", 4), ("S0004", 250)]:
        t = core.tableau_structure(db, id_s, batiments)
        assert len(t) == n
        assert set(t["id_structure"]) == {id_s}
        assert list(t["num"]) == list(range(1, n + 1))


def test_enregistrement_et_isolation(ref, db):
    _, batiments = ref
    t = core.tableau_structure(db, "S0001", batiments)
    t.loc[0, ["statut", "commentaire"]] = [OUI_PETITS, "Menuiseries changées"]
    t.loc[1, "statut"] = "Ne sait pas"
    # Une ligne d'une autre structure glissée dans la saisie est ignorée.
    intrus = core.tableau_structure(db, "S0002", batiments).iloc[[0]].assign(statut="Non")
    assert core.enregistrer_reponses(db, "S0001", pd.concat([t, intrus]), batiments) == 4

    relu = core.tableau_structure(db, "S0001", batiments)
    assert relu.loc[0, "statut"] == OUI_PETITS
    assert relu.loc[0, "commentaire"] == "Menuiseries changées"
    assert relu.loc[1, "statut"] == "Ne sait pas"
    assert core.charger_reponses(db, "S0002").empty


def test_verification_partie1():
    ok = pd.DataFrame([{"id_batiment": "x", "statut": "Non"}, {"id_batiment": "y", "statut": None}])
    assert core.verifier_reponses(ok) == []
    ko = pd.DataFrame([{"id_batiment": "a", "statut": "Peut-être"}])
    assert len(core.verifier_reponses(ko)) == 1


def test_partie2(ref, db):
    _, batiments = ref
    t = core.tableau_structure(db, "S0002", batiments)
    t["statut"] = [OUI_PETITS, OUI_GRANDS, "Non", "Ne sait pas", OUI_PETITS]
    core.enregistrer_reponses(db, "S0002", t, batiments)

    det = core.tableau_details(db, "S0002", batiments)
    assert list(det["num"]) == [1, 2, 5]

    det["travaux"] = [["Ouvrants", "ECS"], None, None]
    det.loc[0, "economie_energie_finale_pct"] = 35
    assert core.verifier_details(det) == []
    # Les travaux sont obligatoires : 2 bâtiments sur 3 n'en ont pas.
    assert len(core.verifier_details(det, complet=True)) == 2
    core.enregistrer_details(db, "S0002", det, batiments)

    relu = core.tableau_details(db, "S0002", batiments)
    assert relu.loc[0, "travaux"] == ["Ouvrants", "ECS"]
    assert relu.loc[0, "economie_energie_finale_pct"] == 35
    assert relu.loc[1, "travaux"] is None or relu.loc[1, "travaux"] != relu.loc[1, "travaux"]

    mauvais = relu.copy()
    mauvais["travaux"] = [["Ouvrants", "Toiture verte"], ["ECS"], ["ECS"]]
    mauvais.loc[1, "economie_energie_finale_pct"] = 140
    assert len(core.verifier_details(mauvais)) == 2

    structures = core.charger_structures()
    export = core.export_complet(db, structures, batiments).set_index("id_batiment")
    assert export.loc["S0002-B001", "travaux"] == "Ouvrants ; ECS"

    # Un bâtiment repassé en « Non » sort de la partie 2 et ses détails sont masqués à l'export.
    t["statut"] = ["Non", OUI_GRANDS, "Non", "Ne sait pas", OUI_PETITS]
    core.enregistrer_reponses(db, "S0002", t, batiments)
    assert list(core.tableau_details(db, "S0002", batiments)["num"]) == [2, 5]
    export = core.export_complet(db, structures, batiments).set_index("id_batiment")
    assert pd.isna(export.loc["S0002-B001", "travaux"])


def test_validation_avancement_export(ref, db):
    structures, batiments = ref
    t = core.tableau_structure(db, "S0002", batiments).assign(statut="Non")
    core.enregistrer_reponses(db, "S0002", t, batiments)
    core.valider(db, "S0002")

    synthese = core.avancement(db, structures, batiments).set_index("id_structure")
    assert synthese.loc["S0002", "nb_renseignes"] == 5
    assert synthese.loc["S0002", "avancement_%"] == 100
    assert synthese.loc["S0002", "valide_le"] != ""
    assert synthese.loc["S0001", "nb_renseignes"] == 0

    export = core.export_complet(db, structures, batiments)
    assert len(export) == len(batiments)
    assert (export.loc[export["id_structure"] == "S0002", "statut"] == "Non").all()
    assert {"travaux", "economie_energie_finale_pct"} <= set(export.columns)


def test_preparer_contacts_multiples():
    ref = pd.DataFrame({
        "id_structure": ["A", "A", "B"],
        "nom_structure": ["Alpha", "Alpha", "Beta"],
        "email": ["a@x.fr; a2@x.fr", "A3@x.fr", "b@x.fr"],
        "nom_batiment": ["École", "Gymnase", "Mairie"],
        "typologie": ["Enseignement", "Sport", "Bureaux"],
    })
    structures, batiments, acces, avert = preparer(ref.copy(), "https://enquete.fr/")
    assert structures.loc[0, "email"] == "a@x.fr, a2@x.fr, a3@x.fr"
    assert list(batiments["id_batiment"]) == ["A-B001", "A-B002", "B-B001"]
    assert "typologie" in batiments.columns
    assert list(acces["email"]) == ["a@x.fr", "a2@x.fr", "a3@x.fr", "b@x.fr"]
    assert acces.loc[0, "lien"] == acces.loc[2, "lien"] == "https://enquete.fr/?structure=A"
    assert acces.loc[3, "lien"] == "https://enquete.fr/?structure=B"
    assert avert == []
    assert list(format_brevo(acces).columns) == [
        "EMAIL", "ID_STRUCTURE", "NOM_STRUCTURE", "NB_BATIMENTS", "LIEN"]


def test_preparer_email_partage_entre_structures():
    ref = pd.DataFrame({
        "id_structure": ["A", "B"], "nom_structure": ["Alpha", "Beta"],
        "email": ["commun@x.fr", "commun@x.fr, b@x.fr"], "nom_batiment": ["École", "Mairie"],
    })
    _, _, acces, avert = preparer(ref, "http://localhost:8501")
    assert len(avert) == 1 and "commun@x.fr" in avert[0]
    assert list(format_brevo(acces)["EMAIL"]) == ["commun@x.fr", "b@x.fr"]


def test_preparer_refuse_email_manquant_ou_invalide():
    base = {"id_structure": ["A"], "nom_structure": ["Alpha"], "nom_batiment": ["École"]}
    with pytest.raises(SystemExit):
        preparer(pd.DataFrame({**base, "email": [""]}), "http://localhost:8501")
    with pytest.raises(SystemExit):
        preparer(pd.DataFrame({**base, "email": ["pas-un-mail"]}), "http://localhost:8501")


def test_une_seule_case_par_ligne():
    avant = pd.DataFrame({"a": [True, False, False], "b": [False, False, False], "c": [False, True, False]})
    # Ligne 0 : on coche « b » en plus de « a » -> « b » remplace « a ».
    # Ligne 1 : rien ne change. Ligne 2 : deux cases cochées d'un coup -> la première.
    apres = pd.DataFrame({"a": [True, False, True], "b": [True, False, True], "c": [False, True, False]})
    corrige = core.une_seule_case(apres, avant)
    assert corrige.values.tolist() == [[False, True, False], [False, False, True], [True, False, False]]
    assert core.une_seule_case(avant, avant) is None
