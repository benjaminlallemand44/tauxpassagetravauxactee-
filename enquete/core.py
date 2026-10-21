"""Logique métier de l'enquête : référentiel, identification, stockage des réponses.

Aucune dépendance à Streamlit ici, pour pouvoir tester sans interface.
"""
from __future__ import annotations

import hmac
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = Path(os.environ.get("ENQUETE_DATA_DIR", RACINE / "data"))

FINANCEMENTS = ["sdie", "audit", "moe", "amo"]

STATUTS = ["Oui – réalisés", "En cours", "Prévus", "Non", "Ne sait pas"]
TYPES_TRAVAUX = [
    "Isolation (murs, toiture, planchers)",
    "Menuiseries",
    "Chauffage / eau chaude",
    "Ventilation",
    "Éclairage",
    "Rénovation globale",
    "Autre",
]
ANNEE_MIN, ANNEE_MAX = 1990, 2035

CHAMPS_REPONSE = ["statut", "type_travaux", "annee", "commentaire"]


# --------------------------------------------------------------------------
# Référentiel
# --------------------------------------------------------------------------
def charger_structures(dossier: Path = DOSSIER_DONNEES) -> pd.DataFrame:
    return pd.read_csv(dossier / "structures.csv", sep=";", dtype=str).fillna("")


def charger_batiments(dossier: Path = DOSSIER_DONNEES) -> pd.DataFrame:
    df = pd.read_csv(dossier / "batiments.csv", sep=";", dtype=str).fillna("")
    df["num"] = df["num"].astype(int)
    return df.sort_values(["id_structure", "num"]).reset_index(drop=True)


def libelle_financement(ligne: pd.Series) -> str:
    finances = [f.upper() for f in FINANCEMENTS if str(ligne.get(f, "")).lower() == "oui"]
    return " + ".join(finances) if finances else "—"


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
    email = (email or "").strip().lower()
    structure = identifier_par_code(structures, code)
    if structure and structure["email"].strip().lower() == email:
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
               type_travaux TEXT,
               annee        INTEGER,
               commentaire  TEXT,
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
        nom = r.get("nom_batiment", r["id_batiment"])
        statut = _nettoyer(r.get("statut"))
        if statut and statut not in STATUTS:
            erreurs.append(f"{nom} : statut inconnu « {statut} ».")
        type_travaux = _nettoyer(r.get("type_travaux"))
        if type_travaux and type_travaux not in TYPES_TRAVAUX:
            erreurs.append(f"{nom} : type de travaux inconnu « {type_travaux} ».")
        annee = _nettoyer(r.get("annee"))
        if annee:
            try:
                a = int(float(annee))
            except ValueError:
                erreurs.append(f"{nom} : année « {annee} » invalide.")
                continue
            if not ANNEE_MIN <= a <= ANNEE_MAX:
                erreurs.append(f"{nom} : année {a} hors de la plage {ANNEE_MIN}–{ANNEE_MAX}.")
    return erreurs


def enregistrer_reponses(db: Path, id_structure: str, reponses: pd.DataFrame,
                         batiments: pd.DataFrame) -> int:
    """Enregistre les réponses d'une structure. Les bâtiments qui n'appartiennent
    pas à la structure sont ignorés. Renvoie le nombre de lignes enregistrées."""
    autorises = set(batiments.loc[batiments["id_structure"] == id_structure, "id_batiment"])
    maintenant = _maintenant()
    lignes = []
    for _, r in reponses.iterrows():
        if r["id_batiment"] not in autorises:
            continue
        annee = _nettoyer(r.get("annee"))
        lignes.append((
            id_structure,
            r["id_batiment"],
            _nettoyer(r.get("statut")),
            _nettoyer(r.get("type_travaux")),
            int(float(annee)) if annee else None,
            _nettoyer(r.get("commentaire")),
            maintenant,
        ))
    with closing(_connexion(db)) as con, con:
        con.executemany(
            """INSERT INTO reponses VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (id_structure, id_batiment) DO UPDATE SET
                 statut = excluded.statut, type_travaux = excluded.type_travaux,
                 annee = excluded.annee, commentaire = excluded.commentaire,
                 maj_le = excluded.maj_le""",
            lignes,
        )
    return len(lignes)


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
    """Bâtiments de la structure avec leurs réponses déjà saisies."""
    bats = batiments[batiments["id_structure"] == id_structure].copy()
    bats["financement"] = bats.apply(libelle_financement, axis=1)
    rep = charger_reponses(db, id_structure).drop(columns=["id_structure", "maj_le"])
    tableau = bats.merge(rep, on="id_batiment", how="left")
    for champ in ["statut", "type_travaux", "commentaire"]:
        tableau[champ] = tableau[champ].fillna("").astype(str)
    tableau["annee"] = pd.to_numeric(tableau["annee"], errors="coerce").astype("Int64")
    return tableau.reset_index(drop=True)


def export_complet(db: Path, structures: pd.DataFrame, batiments: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par bâtiment : référentiel + réponse + validation de la structure."""
    with closing(_connexion(db)) as con:
        rep = pd.read_sql_query("SELECT * FROM reponses", con)
        val = pd.read_sql_query("SELECT * FROM validations", con)
    infos = structures[["id_structure", "nom_structure", "type_structure", "email"]]
    return (
        batiments.merge(infos, on="id_structure", how="left")
        .merge(rep, on=["id_structure", "id_batiment"], how="left")
        .merge(val, on="id_structure", how="left")
    )


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
