import pandas as pd
import pytest

from enquete import core
from preparer_donnees import preparer


@pytest.fixture
def ref():
    return core.charger_structures(), core.charger_batiments()


@pytest.fixture
def db(tmp_path):
    return tmp_path / "reponses.db"


def test_referentiel_de_test(ref):
    structures, batiments = ref
    tailles = batiments.groupby("id_structure").size().to_dict()
    assert tailles == {"S0001": 4, "S0002": 5, "S0003": 80, "S0004": 250, "S0005": 100}
    assert structures["code_acces"].is_unique


def test_identification(ref):
    structures, _ = ref
    s = structures.iloc[2]
    assert core.identifier_par_code(structures, s["code_acces"].lower())["id_structure"] == s["id_structure"]
    assert core.identifier_par_code(structures, "MAUVAIS1") is None
    assert core.identifier_par_code(structures, "") is None
    assert core.identifier_par_email(structures, s["email"].upper(), s["code_acces"])["id_structure"] == s["id_structure"]
    # Le code d'une autre structure ne doit pas ouvrir celle-ci.
    autre = structures.iloc[0]["code_acces"]
    assert core.identifier_par_email(structures, s["email"], autre) is None


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
    t.loc[0, ["statut", "type_travaux", "annee"]] = ["Oui – réalisés", "Menuiseries", 2021]
    t.loc[1, "statut"] = "Prévus"
    # Une ligne d'une autre structure glissée dans la saisie est ignorée.
    intrus = core.tableau_structure(db, "S0002", batiments).iloc[[0]].assign(statut="Non")
    n = core.enregistrer_reponses(db, "S0001", pd.concat([t, intrus]), batiments)
    assert n == 4

    relu = core.tableau_structure(db, "S0001", batiments)
    assert relu.loc[0, "statut"] == "Oui – réalisés"
    assert relu.loc[0, "annee"] == 2021
    assert relu.loc[1, "statut"] == "Prévus"
    assert relu.loc[2, "statut"] == ""
    assert core.charger_reponses(db, "S0002").empty

    # Une nouvelle saisie remplace l'ancienne.
    relu.loc[0, "statut"] = "En cours"
    core.enregistrer_reponses(db, "S0001", relu, batiments)
    assert core.tableau_structure(db, "S0001", batiments).loc[0, "statut"] == "En cours"


def test_verification_des_saisies():
    ok = pd.DataFrame([{"id_batiment": "x", "statut": "Non", "type_travaux": None, "annee": None}])
    assert core.verifier_reponses(ok) == []
    ko = pd.DataFrame([
        {"id_batiment": "a", "statut": "Peut-être", "type_travaux": "", "annee": ""},
        {"id_batiment": "b", "statut": "Non", "type_travaux": "Toiture verte", "annee": ""},
        {"id_batiment": "c", "statut": "Non", "type_travaux": "", "annee": "1850"},
        {"id_batiment": "d", "statut": "Non", "type_travaux": "", "annee": "deux mille"},
    ])
    assert len(core.verifier_reponses(ko)) == 4


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


def test_preparer_conserve_les_codes(tmp_path):
    ref = pd.DataFrame({
        "id_structure": ["A", "A", "B"],
        "nom_structure": ["Alpha", "Alpha", "Beta"],
        "email": ["a@x.fr", "a@x.fr", "b@x.fr"],
        "nom_batiment": ["École", "Gymnase", "Mairie"],
        "audit": ["oui", "", "X"],
    })
    structures, batiments, acces = preparer(ref.copy(), tmp_path, "https://enquete.fr/")
    assert list(batiments["id_batiment"]) == ["A-B001", "A-B002", "B-B001"]
    assert list(batiments["audit"]) == ["Oui", "Non", "Oui"]
    assert acces.loc[0, "lien"] == "https://enquete.fr/?code=" + acces.loc[0, "code_acces"]
    assert list(acces["nb_batiments"]) == [2, 1]

    structures.to_csv(tmp_path / "structures.csv", sep=";", index=False)
    structures2, _, _ = preparer(ref.copy(), tmp_path, "https://enquete.fr")
    assert list(structures2["code_acces"]) == list(structures["code_acces"])


def test_preparer_refuse_deux_emails_pour_une_structure(tmp_path):
    ref = pd.DataFrame({
        "id_structure": ["A", "A"], "nom_structure": ["Alpha", "Alpha"],
        "email": ["a@x.fr", "autre@x.fr"], "nom_batiment": ["École", "Gymnase"],
    })
    with pytest.raises(SystemExit):
        preparer(ref, tmp_path, "http://localhost:8501")
