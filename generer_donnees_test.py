"""Génère un référentiel fictif : 5 structures de 4, 5, 80, 250 et 100 bâtiments,
avec adresse, code postal, commune, typologie, RN et financements reçus
(combinaison de SDIE, Audit, MOE, AMO tirée au hasard).

La structure S0003 a deux contacts, pour tester le code d'accès partagé.

Usage :
  python generer_donnees_test.py                    # écrit data/referentiel_test.csv
  python preparer_donnees.py data/referentiel_test.csv
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from enquete.core import DOSSIER_DONNEES

STRUCTURES = [
    ("S0001", "Commune de Saint-Aubin-les-Prés", "Commune", 4, "test1@votre-domaine.fr"),
    ("S0002", "Communauté de communes du Val d'Orve", "EPCI", 5, "test2@votre-domaine.fr"),
    ("S0003", "Ville de Montclair", "Commune", 80,
     "test3@votre-domaine.fr, test3-bis@votre-domaine.fr"),
    ("S0004", "Département de la Haute-Vallée", "Département", 250, "test4@votre-domaine.fr"),
    ("S0005", "Bailleur social Habitat Roseraie", "Bailleur social", 100, "test5@votre-domaine.fr"),
]

BATIMENTS = {  # type de structure -> [(nom, typologie)]
    "Commune": [("École élémentaire", "Enseignement"), ("École maternelle", "Enseignement"),
                ("Gymnase", "Sport"), ("Mairie annexe", "Bureaux"),
                ("Salle polyvalente", "Culture / loisirs"), ("Médiathèque", "Culture / loisirs"),
                ("Crèche", "Petite enfance"), ("Centre technique", "Technique")],
    "EPCI": [("Siège communautaire", "Bureaux"), ("Piscine intercommunale", "Sport"),
             ("Déchetterie", "Technique"), ("Office de tourisme", "Bureaux"),
             ("Maison de services", "Bureaux")],
    "Département": [("Collège", "Enseignement"), ("Centre médico-social", "Santé / social"),
                    ("Centre d'exploitation routier", "Technique"),
                    ("Archives départementales", "Culture / loisirs"),
                    ("Musée départemental", "Culture / loisirs")],
    "Bailleur social": [("Résidence", "Logement collectif"), ("Immeuble", "Logement collectif"),
                        ("Foyer logement", "Hébergement"), ("Pavillons", "Logement individuel")],
}
NOMS = ["Jaurès", "Pasteur", "Curie", "Moulin", "Hugo", "Ferry", "Zola", "Prévert",
        "Montesquieu", "Les Tilleuls", "Les Peupliers", "Le Parc", "La Fontaine", "Rimbaud"]
RUES = ["rue de la République", "avenue Jean Jaurès", "place de la Mairie", "rue des Écoles",
        "boulevard Victor Hugo", "chemin des Prés", "rue du Stade", "allée des Tilleuls"]
COMMUNES = [("Belcourt", "38110"), ("Saint-Aubin-les-Prés", "38120"), ("Montclair", "38200"),
            ("Varennes", "38210"), ("Les Essarts", "38220"), ("Orvillers", "38230"),
            ("Fontclaire", "38240"), ("Mirande", "38250")]
ALPHABET_RN = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def financements(rnd: random.Random) -> str:
    audit = rnd.random() < 0.6
    tirages = {
        "SDIE": rnd.random() < 0.25,
        "Audit": audit,
        "MOE": rnd.random() < (0.45 if audit else 0.1),  # une MOE suit le plus souvent un audit
        "AMO": rnd.random() < 0.2,
    }
    retenus = [nom for nom, ok in tirages.items() if ok] or ["Audit"]
    return " + ".join(retenus)


def generer(graine: int = 42) -> pd.DataFrame:
    rnd = random.Random(graine)
    lignes = []
    for id_s, nom_s, type_s, nb, emails in STRUCTURES:
        for _ in range(nb):
            nom, typologie = rnd.choice(BATIMENTS[type_s])
            commune, cp = rnd.choice(COMMUNES)
            lignes.append({
                "id_structure": id_s,
                "nom_structure": nom_s,
                "type_structure": type_s,
                "email": emails,
                "nom_batiment": f"{nom} {rnd.choice(NOMS)}",
                "adresse": f"{rnd.randint(1, 120)} {rnd.choice(RUES)}",
                "code_postal": cp,
                "commune": commune,
                "typologie": typologie,
                "rn": "-".join("".join(rnd.choice(ALPHABET_RN) for _ in range(4)) for _ in range(3)),
                "financements": financements(rnd),
            })
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    sortie = Path(DOSSIER_DONNEES) / "referentiel_test.csv"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    generer().to_csv(sortie, sep=";", index=False, encoding="utf-8-sig")
    print(f"Référentiel de test écrit dans {sortie}")
