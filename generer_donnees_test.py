"""Génère un référentiel fictif : 5 structures de 4, 5, 80, 250 et 100 bâtiments,
avec pour chaque bâtiment les financements SDIE / Audit / MOE / AMO tirés au hasard.

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
    ("S0001", "Commune de Saint-Aubin-les-Prés", "Commune", 4),
    ("S0002", "Communauté de communes du Val d'Orve", "EPCI", 5),
    ("S0003", "Ville de Montclair", "Commune", 80),
    ("S0004", "Département de la Haute-Vallée", "Département", 250),
    ("S0005", "Bailleur social Habitat Roseraie", "Bailleur social", 100),
]

TYPES_BATIMENTS = {
    "Commune": ["École élémentaire", "École maternelle", "Gymnase", "Mairie annexe",
                "Salle polyvalente", "Médiathèque", "Crèche", "Centre technique", "Église"],
    "EPCI": ["Siège communautaire", "Piscine intercommunale", "Déchetterie",
             "Office de tourisme", "Maison de services"],
    "Département": ["Collège", "Centre médico-social", "Centre d'exploitation routier",
                    "Archives départementales", "Hôtel du département", "Musée départemental"],
    "Bailleur social": ["Résidence", "Immeuble collectif", "Foyer logement", "Logements individuels"],
}
NOMS = ["Jaurès", "Pasteur", "Curie", "Moulin", "Hugo", "Ferry", "Zola", "Prévert",
        "Montesquieu", "Les Tilleuls", "Les Peupliers", "Le Parc", "La Fontaine", "Rimbaud"]
COMMUNES = ["Belcourt", "Saint-Aubin-les-Prés", "Montclair", "Varennes", "Les Essarts",
            "Orvillers", "Fontclaire", "Mirande", "Haut-Bois", "Prélong"]


def generer(graine: int = 42) -> pd.DataFrame:
    rnd = random.Random(graine)
    lignes = []
    for i, (id_s, nom_s, type_s, nb) in enumerate(STRUCTURES, start=1):
        for k in range(1, nb + 1):
            audit = rnd.random() < 0.55
            lignes.append({
                "id_structure": id_s,
                "nom_structure": nom_s,
                "type_structure": type_s,
                "email": f"test{i}@votre-domaine.fr",
                "nom_batiment": f"{rnd.choice(TYPES_BATIMENTS[type_s])} {rnd.choice(NOMS)}",
                "commune": rnd.choice(COMMUNES),
                "surface_m2": rnd.randrange(80, 9000, 10),
                "annee_construction": rnd.randrange(1880, 2015),
                "sdie": "Oui" if rnd.random() < 0.25 else "Non",
                "audit": "Oui" if audit else "Non",
                # Une MOE suit le plus souvent un audit.
                "moe": "Oui" if rnd.random() < (0.45 if audit else 0.1) else "Non",
                "amo": "Oui" if rnd.random() < 0.2 else "Non",
            })
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    sortie = Path(DOSSIER_DONNEES) / "referentiel_test.csv"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    generer().to_csv(sortie, sep=";", index=False, encoding="utf-8-sig")
    print(f"Référentiel de test écrit dans {sortie}")
