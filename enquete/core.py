"""Logique métier de l'enquête : référentiel, identification, stockage des réponses.

Aucune dépendance à Streamlit ici, pour pouvoir tester sans interface.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

from enquete.questionnaire import (QUESTIONS_PARTIE2, STATUT_SI_MOE, STATUTS,
                                   STATUTS_DETAILLES)

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = Path(os.environ.get("ENQUETE_DATA_DIR", RACINE / "data"))
FICHIER_DEFINITIONS = RACINE / "contenu" / "definitions.md"
ANNEE_MIN, ANNEE_MAX = 1990, 2035

# Colonnes Oui/Non regroupées en une seule colonne « Financements » à l'affichage.
FINANCEMENTS = ["sdie", "audit", "moe", "amo"]
# Colonnes du référentiel qui ne sont pas montrées dans le tableau des bâtiments.
COLONNES_INTERNES = {"id_structure", "nom_structure", "type_structure", "email", "id_batiment"}
LIBELLES = {
    "num": "N°",
    "nom_batiment": "Bâtiment",
    "adresse": "Adresse",
    "code_postal": "Code postal",
    "commune": "Commune",
    "typologie": "Typologie",
    "rn": "RN",
    "financement": "Financements reçus",
    "financements": "Financements reçus",
    "surface_m2": "Surface (m²)",
    "annee_construction": "Année de construction",
}


# --------------------------------------------------------------------------
# Référentiel
# --------------------------------------------------------------------------
def separer_emails(texte: str) -> list[str]:
    """« a@x.fr ; B@y.fr » -> ["a@x.fr", "b@y.fr"]"""
    return [e.lower() for e in re.split(r"[,;\s]+", texte or "") if e]


def charger_structures(dossier: Path = DOSSIER_DONNEES) -> pd.DataFrame:
    return pd.read_csv(dossier / "structures.csv", sep=";", dtype=str).fillna("")


def charger_batiments(dossier: Path = DOSSIER_DONNEES) -> pd.DataFrame:
    df = pd.read_csv(dossier / "batiments.csv", sep=";", dtype=str).fillna("")
    df["num"] = df["num"].astype(int)
    return df.sort_values(["id_structure", "num"]).reset_index(drop=True)


def libelle_financement(ligne: pd.Series) -> str:
    finances = [f.upper() for f in FINANCEMENTS if str(ligne.get(f, "")).lower() == "oui"]
    return " + ".join(finances) if finances else "—"


def a_recu_moe(ligne: pd.Series) -> bool:
    """MOE dans les colonnes Oui/Non, ou mentionnée dans une colonne texte de financements."""
    if str(ligne.get("moe", "")).lower() == "oui":
        return True
    return any(
        re.search(r"\bMOE\b|ma[iî]trise d.[œo]e?uvre", str(v), re.IGNORECASE)
        for col, v in ligne.items()
        if "financ" in col and col != "financement"
    )


def colonnes_affichees(batiments: pd.DataFrame) -> list[str]:
    """Colonnes du référentiel montrées au répondant, dans l'ordre du fichier."""
    colonnes = ["num"] + [
        c for c in batiments.columns
        if c not in COLONNES_INTERNES and c not in FINANCEMENTS and c != "num"
    ]
    if any(f in batiments.columns for f in FINANCEMENTS):
        colonnes.append("financement")
    return colonnes


def libelle(colonne: str) -> str:
    return LIBELLES.get(colonne, colonne.replace("_", " ").capitalize())


def charger_definitions() -> str:
    return FICHIER_DEFINITIONS.read_text(encoding="utf-8") if FICHIER_DEFINITIONS.exists() else ""


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------
def _egal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def identifier_par_code(structures: pd.DataFrame, code: str) -> dict | None:
    code = (code or "").strip().upper()
    if not code:
        return None
    for _, s in structures.iterrows():
        if _egal(s["code_acces"].upper(), code):
            return s.to_dict()
    return None


def identifier_par_email(structures: pd.DataFrame, email: str, code: str) -> dict | None:
    """Le code est celui de la structure ; l'e-mail doit être l'un de ses contacts."""
    email = (email or "").strip().lower()
    structure = identifier_par_code(structures, code)
    if structure and email in separer_emails(structure["email"]):
        return structure
    return None


# --------------------------------------------------------------------------
# Stockage (SQLite)
# --------------------------------------------------------------------------
def chemin_base() -> Path:
    return Path(os.environ.get("ENQUETE_DB", DOSSIER_DONNEES / "reponses.db"))


def _connexion(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute(
        """CREATE TABLE IF NOT EXISTS reponses (
               id_structure TEXT NOT NULL,
               id_batiment  TEXT NOT NULL,
               statut       TEXT,
               commentaire  TEXT,
               maj_le       TEXT NOT NULL,
               PRIMARY KEY (id_structure, id_batiment))"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS details (
               id_structure TEXT NOT NULL,
               id_batiment  TEXT NOT NULL,
               donnees      TEXT NOT NULL,
               maj_le       TEXT NOT NULL,
               PRIMARY KEY (id_structure, id_batiment))"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS validations (
               id_structure TEXT PRIMARY KEY,
               valide_le    TEXT NOT NULL)"""
    )
    return con


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def charger_reponses(db: Path, id_structure: str) -> pd.DataFrame:
    with closing(_connexion(db)) as con:
        return pd.read_sql_query(
            "SELECT * FROM reponses WHERE id_structure = ?", con, params=(id_structure,)
        )


def _nettoyer(valeur) -> str:
    if valeur is None or (pd.api.types.is_scalar(valeur) and pd.isna(valeur)):
        return ""
    return str(valeur).strip()


def verifier_reponses(reponses: pd.DataFrame) -> list[str]:
    """Renvoie la liste des erreurs de saisie (vide si tout est correct)."""
    erreurs = []
    for _, r in reponses.iterrows():
        statut = _nettoyer(r.get("statut"))
        if statut and statut not in STATUTS:
            nom = r.get("nom_batiment", r["id_batiment"])
            erreurs.append(f"{nom} : réponse inconnue « {statut} ».")
    return erreurs


def enregistrer_reponses(db: Path, id_structure: str, reponses: pd.DataFrame,
                         batiments: pd.DataFrame) -> int:
    """Enregistre les réponses d'une structure. Les bâtiments qui n'appartiennent
    pas à la structure sont ignorés. Renvoie le nombre de lignes enregistrées."""
    autorises = set(batiments.loc[batiments["id_structure"] == id_structure, "id_batiment"])
    maintenant = _maintenant()
    lignes = [
        (id_structure, r["id_batiment"], _nettoyer(r.get("statut")),
         _nettoyer(r.get("commentaire")), maintenant)
        for _, r in reponses.iterrows()
        if r["id_batiment"] in autorises
    ]
    with closing(_connexion(db)) as con, con:
        con.executemany(
            """INSERT INTO reponses VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (id_structure, id_batiment) DO UPDATE SET
                 statut = excluded.statut, commentaire = excluded.commentaire,
                 maj_le = excluded.maj_le""",
            lignes,
        )
    return len(lignes)


def _valeur_detail(question: dict, valeur):
    valeur = _nettoyer(valeur)
    if not valeur:
        return None
    if question["type"] in ("nombre", "annee"):
        nombre = float(valeur.replace(",", ".").replace(" ", ""))
        return int(nombre) if question["type"] == "annee" or nombre.is_integer() else nombre
    return valeur


def verifier_details(details: pd.DataFrame, questions: list[dict] = QUESTIONS_PARTIE2,
                     complet: bool = False) -> list[str]:
    """Erreurs de saisie de la partie 2 ; avec complet=True, signale aussi les
    questions obligatoires non remplies."""
    erreurs = []
    for _, r in details.iterrows():
        nom = r.get("nom_batiment", r["id_batiment"])
        for q in questions:
            brut = _nettoyer(r.get(q["cle"]))
            if not brut:
                if complet and q.get("obligatoire"):
                    erreurs.append(f"{nom} : « {q['libelle']} » est à renseigner.")
                continue
            if q["type"] == "choix" and brut not in q["options"]:
                erreurs.append(f"{nom} : « {brut} » n'est pas une réponse possible pour « {q['libelle']} ».")
            elif q["type"] in ("nombre", "annee"):
                try:
                    v = _valeur_detail(q, brut)
                except ValueError:
                    erreurs.append(f"{nom} : « {brut} » n'est pas un nombre ({q['libelle']}).")
                    continue
                if q["type"] == "annee" and not ANNEE_MIN <= v <= ANNEE_MAX:
                    erreurs.append(f"{nom} : année {v} hors de la plage {ANNEE_MIN}–{ANNEE_MAX}.")
    return erreurs


def enregistrer_details(db: Path, id_structure: str, details: pd.DataFrame,
                        batiments: pd.DataFrame, questions: list[dict] = QUESTIONS_PARTIE2) -> int:
    autorises = set(batiments.loc[batiments["id_structure"] == id_structure, "id_batiment"])
    maintenant = _maintenant()
    lignes = [
        (id_structure, r["id_batiment"],
         json.dumps({q["cle"]: _valeur_detail(q, r.get(q["cle"])) for q in questions},
                    ensure_ascii=False),
         maintenant)
        for _, r in details.iterrows()
        if r["id_batiment"] in autorises
    ]
    with closing(_connexion(db)) as con, con:
        con.executemany(
            """INSERT INTO details VALUES (?, ?, ?, ?)
               ON CONFLICT (id_structure, id_batiment) DO UPDATE SET
                 donnees = excluded.donnees, maj_le = excluded.maj_le""",
            lignes,
        )
    return len(lignes)


def _details_en_colonnes(brut: pd.DataFrame, questions: list[dict]) -> pd.DataFrame:
    cles = [q["cle"] for q in questions]
    if brut.empty:
        return pd.DataFrame(columns=["id_structure", "id_batiment", *cles])
    valeurs = pd.DataFrame([json.loads(d) for d in brut["donnees"]], index=brut.index)
    return pd.concat([brut[["id_structure", "id_batiment"]], valeurs.reindex(columns=cles)], axis=1)


def valider(db: Path, id_structure: str) -> None:
    with closing(_connexion(db)) as con, con:
        con.execute(
            "INSERT OR REPLACE INTO validations VALUES (?, ?)", (id_structure, _maintenant())
        )


def date_validation(db: Path, id_structure: str) -> str | None:
    with closing(_connexion(db)) as con:
        ligne = con.execute(
            "SELECT valide_le FROM validations WHERE id_structure = ?", (id_structure,)
        ).fetchone()
    return ligne[0] if ligne else None


# --------------------------------------------------------------------------
# Vues combinées
# --------------------------------------------------------------------------
def tableau_structure(db: Path, id_structure: str, batiments: pd.DataFrame) -> pd.DataFrame:
    """Bâtiments de la structure avec leurs réponses déjà saisies. Un bâtiment jamais
    enregistré ayant reçu une MOE est pré-rempli avec STATUT_SI_MOE (colonne pre_rempli)."""
    bats = batiments[batiments["id_structure"] == id_structure].copy()
    if any(f in bats.columns for f in FINANCEMENTS):
        bats["financement"] = bats.apply(libelle_financement, axis=1) if len(bats) else ""
    rep = charger_reponses(db, id_structure).drop(columns=["id_structure"])
    tableau = bats.merge(rep, on="id_batiment", how="left")
    jamais_enregistre = tableau["maj_le"].isna()
    moe = tableau.apply(a_recu_moe, axis=1) if len(tableau) else pd.Series(dtype=bool)
    tableau["pre_rempli"] = bool(STATUT_SI_MOE) & jamais_enregistre & moe
    tableau.loc[tableau["pre_rempli"], "statut"] = STATUT_SI_MOE
    for champ in ["statut", "commentaire"]:
        tableau[champ] = tableau[champ].fillna("").astype(str)
    return tableau.drop(columns=["maj_le"]).reset_index(drop=True)


def tableau_details(db: Path, id_structure: str, batiments: pd.DataFrame,
                    questions: list[dict] = QUESTIONS_PARTIE2) -> pd.DataFrame:
    """Partie 2 : bâtiments dont la réponse ENREGISTRÉE ouvre les détails."""
    tableau = tableau_structure(db, id_structure, batiments)
    concernes = tableau[tableau["statut"].isin(STATUTS_DETAILLES) & ~tableau["pre_rempli"]]
    with closing(_connexion(db)) as con:
        brut = pd.read_sql_query(
            "SELECT * FROM details WHERE id_structure = ?", con, params=(id_structure,))
    details = _details_en_colonnes(brut, questions).drop(columns=["id_structure"])
    return concernes.merge(details, on="id_batiment", how="left").reset_index(drop=True)


def export_complet(db: Path, structures: pd.DataFrame, batiments: pd.DataFrame,
                   questions: list[dict] = QUESTIONS_PARTIE2) -> pd.DataFrame:
    """Une ligne par bâtiment : référentiel + réponses (parties 1 et 2) + validation."""
    with closing(_connexion(db)) as con:
        rep = pd.read_sql_query("SELECT * FROM reponses", con)
        det = pd.read_sql_query("SELECT * FROM details", con)
        val = pd.read_sql_query("SELECT * FROM validations", con)
    infos = structures[["id_structure", "nom_structure", "type_structure", "email"]]
    export = (
        batiments.merge(infos, on="id_structure", how="left")
        .merge(rep, on=["id_structure", "id_batiment"], how="left")
        .merge(_details_en_colonnes(det, questions), on=["id_structure", "id_batiment"], how="left")
        .merge(val, on="id_structure", how="left")
    )
    # Détails d'un bâtiment dont la réponse a ensuite été changée en « Non » : on les masque.
    hors_partie2 = ~export["statut"].isin(STATUTS_DETAILLES)
    export.loc[hors_partie2, [q["cle"] for q in questions]] = None
    return export


def avancement(db: Path, structures: pd.DataFrame, batiments: pd.DataFrame) -> pd.DataFrame:
    export = export_complet(db, structures, batiments)
    export["renseigne"] = export["statut"].fillna("").ne("")
    synthese = (
        export.groupby(["id_structure", "nom_structure"], sort=False)
        .agg(nb_batiments=("id_batiment", "size"),
             nb_renseignes=("renseigne", "sum"),
             valide_le=("valide_le", "first"))
        .reset_index()
    )
    synthese["avancement_%"] = (100 * synthese["nb_renseignes"] / synthese["nb_batiments"]).round()
    synthese["valide_le"] = synthese["valide_le"].fillna("")
    return synthese
