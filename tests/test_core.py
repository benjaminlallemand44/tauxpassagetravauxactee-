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
    assert structures["code_acces"].is_unique
    assert core.colonnes_affichees(batiments) == [
        "num", "nom_batiment", "adresse", "code_postal", "commune", "typologie", "rn", "financements"]


def test_identification(ref):
    structures, _ = ref
    s = structures.set_index("id_structure").loc["S0003"]
    assert core.identifier_par_code(structures, s["code_acces"].lower())["id_structure"] == "S0003"
    assert core.identifier_par_code(structures, "MAUVAIS1") is None
    assert core.identifier_par_code(structures, "") is None
    # Les deux contacts de la structure se connectent avec le même code.
    for email in ["test3@votre-domaine.fr", "TEST3-BIS@votre-domaine.fr"]:
        assert core.identifier_par_email(structures, email, s["code_acces"])["id_structure"] == "S0003"
    # Le code d'une autre structure ne doit pas ouvrir celle-ci.
    autre = structures.set_index("id_structure").loc["S0001", "code_acces"]
    assert core.identifier_par_email(structures, "test3@votre-domaine.fr", autre) is None


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

    det.loc[0, ["annee_fin_travaux", "nature_travaux", "montant_ht"]] = [2022, "Menuiseries", 45000]
    assert core.verifier_details(det) == []
    # L'année est obligatoire : 2 bâtiments sur 3 ne l'ont pas.
    assert len(core.verifier_details(det, complet=True)) == 2
    core.enregistrer_details(db, "S0002", det, batiments)

    relu = core.tableau_details(db, "S0002", batiments)
    assert relu.loc[0, "annee_fin_travaux"] == 2022
    assert relu.loc[0, "nature_travaux"] == "Menuiseries"
    assert relu.loc[0, "montant_ht"] == 45000
    assert pd.isna(relu.loc[1, "annee_fin_travaux"])

    mauvais = relu.copy()
    mauvais.loc[1, "annee_fin_travaux"] = 1850
    mauvais.loc[2, "nature_travaux"] = "Toiture verte"
    assert len(core.verifier_details(mauvais)) == 2

    # Un bâtiment repassé en « Non » sort de la partie 2 et ses détails sont masqués à l'export.
    t["statut"] = ["Non", OUI_GRANDS, "Non", "Ne sait pas", OUI_PETITS]
    core.enregistrer_reponses(db, "S0002", t, batiments)
    assert list(core.tableau_details(db, "S0002", batiments)["num"]) == [2, 5]
    structures = core.charger_structures()
    export = core.export_complet(db, structures, batiments).set_index("id_batiment")
    assert pd.isna(export.loc["S0002-B001", "annee_fin_travaux"])


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
    assert "annee_fin_travaux" in export.columns


def test_preparer_contacts_multiples_et_codes_conserves(tmp_path):
    ref = pd.DataFrame({
        "id_structure": ["A", "A", "B"],
        "nom_structure": ["Alpha", "Alpha", "Beta"],
        "email": ["a@x.fr; a2@x.fr", "A3@x.fr", "b@x.fr"],
        "nom_batiment": ["École", "Gymnase", "Mairie"],
        "typologie": ["Enseignement", "Sport", "Bureaux"],
    })
    structures, batiments, acces, avert = preparer(ref.copy(), tmp_path, "https://enquete.fr/")
    assert structures.loc[0, "email"] == "a@x.fr, a2@x.fr, a3@x.fr"
    assert list(batiments["id_batiment"]) == ["A-B001", "A-B002", "B-B001"]
    assert "typologie" in batiments.columns
    assert list(acces["email"]) == ["a@x.fr", "a2@x.fr", "a3@x.fr", "b@x.fr"]
    assert acces.loc[0, "code_acces"] == acces.loc[2, "code_acces"] != acces.loc[3, "code_acces"]
    assert acces.loc[0, "lien"] == "https://enquete.fr/?code=" + acces.loc[0, "code_acces"]
    assert avert == []
    assert list(format_brevo(acces).columns) == [
        "EMAIL", "ID_STRUCTURE", "NOM_STRUCTURE", "NB_BATIMENTS", "CODE_ACCES", "LIEN"]

    structures.to_csv(tmp_path / "structures.csv", sep=";", index=False)
    structures2, *_ = preparer(ref.copy(), tmp_path, "https://enquete.fr")
    assert list(structures2["code_acces"]) == list(structures["code_acces"])


def test_preparer_email_partage_entre_structures(tmp_path):
    ref = pd.DataFrame({
        "id_structure": ["A", "B"], "nom_structure": ["Alpha", "Beta"],
        "email": ["commun@x.fr", "commun@x.fr, b@x.fr"], "nom_batiment": ["École", "Mairie"],
    })
    _, _, acces, avert = preparer(ref, tmp_path, "http://localhost:8501")
    assert len(avert) == 1 and "commun@x.fr" in avert[0]
    assert list(format_brevo(acces)["EMAIL"]) == ["commun@x.fr", "b@x.fr"]


def test_preparer_refuse_email_manquant_ou_invalide(tmp_path):
    base = {"id_structure": ["A"], "nom_structure": ["Alpha"], "nom_batiment": ["École"]}
    with pytest.raises(SystemExit):
        preparer(pd.DataFrame({**base, "email": [""]}), tmp_path, "http://localhost:8501")
    with pytest.raises(SystemExit):
        preparer(pd.DataFrame({**base, "email": ["pas-un-mail"]}), tmp_path, "http://localhost:8501")
