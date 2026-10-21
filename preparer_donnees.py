"""Prépare les fichiers de l'application à partir d'un référentiel structures × bâtiments.

Entrée : un fichier Excel (.xlsx) ou CSV (séparateur « ; ») avec une ligne par bâtiment.
  Colonnes obligatoires : id_structure, nom_structure, email, nom_batiment
  Colonnes facultatives : type_structure, id_batiment, commune, surface_m2,
                          annee_construction, sdie, audit, moe, amo (Oui/Non)

Sorties (dans data/ par défaut) :
  structures.csv  une ligne par structure, avec son code d'accès
  batiments.csv   une ligne par bâtiment, numérotés 1..n dans chaque structure
  acces.csv       e-mail, structure, code et lien personnel : à utiliser pour le publipostage

Les codes déjà attribués (structures.csv existant) sont conservés : on peut relancer
le script après une correction du référentiel sans invalider les liens déjà envoyés.

Usage :
  python preparer_donnees.py referentiel.xlsx --base-url https://enquete.mondomaine.fr
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

import pandas as pd

from enquete.core import DOSSIER_DONNEES, FINANCEMENTS

OBLIGATOIRES = ["id_structure", "nom_structure", "email", "nom_batiment"]
FACULTATIVES = ["type_structure", "id_batiment", "commune", "surface_m2", "annee_construction"]
# Pas de 0/O ni 1/I/L : les codes sont recopiés à la main par certains répondants.
ALPHABET_CODE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_CODE = 8


def lire_referentiel(chemin: Path) -> pd.DataFrame:
    if chemin.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(chemin, dtype=str)
    else:
        df = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    manquantes = [c for c in OBLIGATOIRES if c not in df.columns]
    if manquantes:
        raise SystemExit(f"Colonnes obligatoires manquantes : {', '.join(manquantes)}")
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def oui_non(valeur: str) -> str:
    return "Oui" if valeur.strip().lower() in {"oui", "o", "yes", "y", "1", "x", "vrai", "true"} else "Non"


def nouveau_code(existants: set[str]) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
        if code not in existants:
            existants.add(code)
            return code


def preparer(ref: pd.DataFrame, dossier: Path, base_url: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for col in FACULTATIVES + FINANCEMENTS:
        if col not in ref.columns:
            ref[col] = ""
    for col in FINANCEMENTS:
        ref[col] = ref[col].map(oui_non)

    # Une structure = un e-mail, un nom : on signale les incohérences au lieu de choisir au hasard.
    infos = ref.groupby("id_structure", sort=False).agg(
        nom_structure=("nom_structure", "first"),
        type_structure=("type_structure", "first"),
        email=("email", "first"),
        nb_emails=("email", "nunique"),
    ).reset_index()
    incoherents = infos.loc[infos["nb_emails"] > 1, "id_structure"].tolist()
    if incoherents:
        raise SystemExit(f"Plusieurs e-mails pour les structures : {', '.join(incoherents)}")
    sans_email = infos.loc[infos["email"] == "", "id_structure"].tolist()
    if sans_email:
        raise SystemExit(f"E-mail manquant pour les structures : {', '.join(sans_email)}")

    anciens = {}
    if (dossier / "structures.csv").exists():
        prec = pd.read_csv(dossier / "structures.csv", sep=";", dtype=str).fillna("")
        anciens = dict(zip(prec["id_structure"], prec["code_acces"]))
    utilises = set(anciens.values())
    infos["code_acces"] = [anciens.get(i) or nouveau_code(utilises) for i in infos["id_structure"]]
    structures = infos[["id_structure", "nom_structure", "type_structure", "email", "code_acces"]]

    ref["num"] = ref.groupby("id_structure", sort=False).cumcount() + 1
    sans_id = ref["id_batiment"] == ""
    ref.loc[sans_id, "id_batiment"] = (
        ref.loc[sans_id, "id_structure"] + "-B" + ref.loc[sans_id, "num"].astype(str).str.zfill(3)
    )
    doublons = ref.loc[ref["id_batiment"].duplicated(), "id_batiment"].tolist()
    if doublons:
        raise SystemExit(f"Identifiants de bâtiment en double : {', '.join(doublons[:10])}")
    batiments = ref[["id_structure", "num", "id_batiment", "nom_batiment", "commune",
                     "surface_m2", "annee_construction", *FINANCEMENTS]]

    acces = structures.merge(
        batiments.groupby("id_structure").size().rename("nb_batiments").reset_index(),
        on="id_structure",
    )
    acces["lien"] = base_url.rstrip("/") + "/?code=" + acces["code_acces"]
    acces = acces[["email", "id_structure", "nom_structure", "nb_batiments", "code_acces", "lien"]]
    return structures, batiments, acces


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("referentiel", type=Path)
    parser.add_argument("--base-url", default="http://localhost:8501",
                        help="adresse publique de l'application (pour les liens personnels)")
    parser.add_argument("--sortie", type=Path, default=DOSSIER_DONNEES)
    args = parser.parse_args(argv)

    args.sortie.mkdir(parents=True, exist_ok=True)
    structures, batiments, acces = preparer(lire_referentiel(args.referentiel), args.sortie, args.base_url)
    structures.to_csv(args.sortie / "structures.csv", sep=";", index=False)
    batiments.to_csv(args.sortie / "batiments.csv", sep=";", index=False)
    # utf-8-sig : s'ouvre correctement dans Excel pour le publipostage.
    acces.to_csv(args.sortie / "acces.csv", sep=";", index=False, encoding="utf-8-sig")
    print(f"{len(structures)} structures, {len(batiments)} bâtiments -> {args.sortie}", file=sys.stderr)


if __name__ == "__main__":
    main()
