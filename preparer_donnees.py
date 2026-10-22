"""Prépare les fichiers de l'application à partir d'un référentiel structures × bâtiments.

Entrée : un fichier Excel (.xlsx) ou CSV (séparateur « ; ») avec une ligne par bâtiment.
  Colonnes obligatoires : id_structure, nom_structure, email, nom_batiment
  Colonnes facultatives : type_structure, id_batiment, et toutes les colonnes
                          descriptives du bâtiment (adresse, code_postal, commune,
                          typologie, rn…) : elles sont affichées telles quelles,
                          dans l'ordre du fichier.
  Financements : colonnes sdie, audit, moe, amo (Oui/Non), regroupées à l'affichage,
                 ou une seule colonne texte (ex. « financements »).

Plusieurs e-mails par structure : séparez-les par « , » ou « ; » dans la cellule, ou
mettez des e-mails différents sur des lignes de la même structure. Tous les contacts
d'une structure reçoivent le même lien.

Sorties (dans data/ par défaut) :
  structures.csv        une ligne par structure
  batiments.csv         une ligne par bâtiment, numérotés 1..n dans chaque structure
  acces.csv             une ligne par contact : e-mail, structure, lien direct
  brevo_contacts.csv    le même fichier au format d'import Brevo (attributs en majuscules)

Usage :
  python preparer_donnees.py referentiel.xlsx --base-url https://enquete.mondomaine.fr
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from enquete.core import DOSSIER_DONNEES, FINANCEMENTS, separer_emails

OBLIGATOIRES = ["id_structure", "nom_structure", "email", "nom_batiment"]


def lire_referentiel(chemin: Path) -> pd.DataFrame:
    if chemin.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(chemin, dtype=str)
    else:
        df = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    manquantes = [c for c in OBLIGATOIRES if c not in df.columns]
    if manquantes:
        raise SystemExit(f"Colonnes obligatoires manquantes : {', '.join(manquantes)}")
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def oui_non(valeur: str) -> str:
    return "Oui" if valeur.strip().lower() in {"oui", "o", "yes", "y", "1", "x", "vrai", "true"} else "Non"


def _emails_uniques(cellules: pd.Series) -> str:
    vus = []
    for cellule in cellules:
        for e in separer_emails(cellule):
            if e not in vus:
                vus.append(e)
    return ", ".join(vus)


def preparer(ref: pd.DataFrame, base_url: str):
    """Renvoie (structures, batiments, acces, avertissements)."""
    avertissements = []
    if "type_structure" not in ref.columns:
        ref["type_structure"] = ""
    if "id_batiment" not in ref.columns:
        ref["id_batiment"] = ""
    for col in FINANCEMENTS:
        if col in ref.columns:
            ref[col] = ref[col].map(oui_non)

    infos = ref.groupby("id_structure", sort=False).agg(
        nom_structure=("nom_structure", "first"),
        type_structure=("type_structure", "first"),
        email=("email", _emails_uniques),
    ).reset_index()
    sans_email = infos.loc[infos["email"] == "", "id_structure"].tolist()
    if sans_email:
        raise SystemExit(f"E-mail manquant pour les structures : {', '.join(sans_email)}")
    invalides = sorted({e for l in infos["email"] for e in separer_emails(l) if "@" not in e})
    if invalides:
        raise SystemExit(f"Adresses e-mail invalides : {', '.join(invalides)}")

    structures = infos[["id_structure", "nom_structure", "type_structure", "email"]]

    ref["num"] = ref.groupby("id_structure", sort=False).cumcount() + 1
    sans_id = ref["id_batiment"] == ""
    ref.loc[sans_id, "id_batiment"] = (
        ref.loc[sans_id, "id_structure"] + "-B" + ref.loc[sans_id, "num"].astype(str).str.zfill(3)
    )
    doublons = ref.loc[ref["id_batiment"].duplicated(), "id_batiment"].tolist()
    if doublons:
        raise SystemExit(f"Identifiants de bâtiment en double : {', '.join(doublons[:10])}")
    # Toutes les colonnes descriptives du fichier sont conservées, dans leur ordre.
    descriptives = [c for c in ref.columns
                    if c not in {"id_structure", "nom_structure", "type_structure", "email",
                                 "id_batiment", "num"}]
    batiments = ref[["id_structure", "num", "id_batiment", *descriptives]]

    nb_bat = batiments.groupby("id_structure").size().rename("nb_batiments").reset_index()
    acces = structures.merge(nb_bat, on="id_structure")
    acces["email"] = acces["email"].map(separer_emails)
    acces = acces.explode("email", ignore_index=True)
    acces["lien"] = base_url.rstrip("/") + "/?structure=" + acces["id_structure"]
    acces = acces[["email", "id_structure", "nom_structure", "nb_batiments", "lien"]]

    partages = acces.loc[acces["email"].duplicated(keep=False)]
    for email, groupe in partages.groupby("email"):
        avertissements.append(
            f"{email} est contact de plusieurs structures ({', '.join(groupe['id_structure'])}) : "
            "Brevo ne garde qu'un lien par contact, seule la première structure figure dans "
            "brevo_contacts.csv. Envoyez-lui les autres liens séparément."
        )
    return structures, batiments, acces, avertissements


def format_brevo(acces: pd.DataFrame) -> pd.DataFrame:
    """Un contact par ligne, attributs en majuscules comme dans Brevo."""
    brevo = acces.drop_duplicates("email").rename(columns=str.upper)
    return brevo[["EMAIL", "ID_STRUCTURE", "NOM_STRUCTURE", "NB_BATIMENTS", "LIEN"]]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("referentiel", type=Path)
    parser.add_argument("--base-url", default="http://localhost:8501",
                        help="adresse publique de l'application (pour les liens personnels)")
    parser.add_argument("--sortie", type=Path, default=DOSSIER_DONNEES)
    args = parser.parse_args(argv)

    args.sortie.mkdir(parents=True, exist_ok=True)
    structures, batiments, acces, avertissements = preparer(
        lire_referentiel(args.referentiel), args.base_url)
    structures.to_csv(args.sortie / "structures.csv", sep=";", index=False)
    batiments.to_csv(args.sortie / "batiments.csv", sep=";", index=False)
    # utf-8-sig : s'ouvre correctement dans Excel.
    acces.to_csv(args.sortie / "acces.csv", sep=";", index=False, encoding="utf-8-sig")
    format_brevo(acces).to_csv(args.sortie / "brevo_contacts.csv", sep=";", index=False, encoding="utf-8")
    for a in avertissements:
        print("Attention :", a, file=sys.stderr)
    print(f"{len(structures)} structures, {len(acces)} contacts, {len(batiments)} bâtiments -> {args.sortie}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
