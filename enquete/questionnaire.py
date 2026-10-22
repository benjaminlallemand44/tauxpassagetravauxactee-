"""Contenu du questionnaire : c'est ici qu'on modifie les questions et les réponses.

Les définitions des petits et grands travaux se trouvent dans contenu/definitions.md.
"""

# --------------------------------------------------------------------------
# Partie 1 : une réponse par bâtiment, une case à cocher par réponse possible
# --------------------------------------------------------------------------
QUESTION = "Est-ce que les bâtiments suivants sont passés en travaux de rénovation énergétique ?"

OUI_PETITS = "Oui, en petits travaux"
OUI_GRANDS = "Oui, en grands travaux de rénovation énergétique"
STATUTS = [
    OUI_PETITS,
    OUI_GRANDS,
    "Non, mais je planifie de faire les travaux dans les 5 ans",
    "Non",
    "Ne sait pas",
]
STATUT_NON = "Non"

# Titre de chaque colonne à cocher (le libellé complet s'affiche en info-bulle).
TITRES_COLONNES = {
    OUI_PETITS: "Oui, petits",
    OUI_GRANDS: "Oui, grands",
    "Non, mais je planifie de faire les travaux dans les 5 ans": "Prévus < 5 ans",
    "Non": "Non",
    "Ne sait pas": "Ne sait pas",
}

# Réponses qui ouvrent la partie 2 pour le bâtiment.
STATUTS_DETAILLES = [OUI_PETITS, OUI_GRANDS]

# Réponse pré-cochée quand « MOE » figure parmi les financements du bâtiment.
# Le répondant peut la modifier. Mettre None pour désactiver la pré-sélection.
STATUT_SI_MOE = OUI_GRANDS

# Colonnes du référentiel qui ne sont pas montrées au répondant (elles restent dans l'export).
COLONNES_MASQUEES = {"rn"}

# --------------------------------------------------------------------------
# Partie 2 : détails pour les bâtiments ayant répondu « Oui »
# --------------------------------------------------------------------------
# Chaque question devient une colonne du tableau de la partie 2.
#   cle          nom de la colonne dans l'export (sans espace ni accent)
#   libelle      titre de la colonne affiché au répondant
#   type         "choix" (liste déroulante), "choix_multiple", "texte", "nombre",
#                "pourcentage" ou "annee"
#   options      pour "choix" et "choix_multiple"
#   aide         (facultatif) info-bulle sur la colonne
#   obligatoire  (facultatif) à remplir avant de pouvoir valider
QUESTIONS_PARTIE2 = [
    {
        "cle": "travaux",
        "libelle": "Travaux réalisés ou en cours",
        "type": "choix_multiple",
        "aide": "Plusieurs choix possibles.",
        "obligatoire": True,
        "options": [
            "Isolation des murs",
            "Isolation du plancher",
            "Étanchéité à l'air",
            "Ouvrants",
            "Isolation des combles/toiture",
            "Système de chauffage",
            "Système de ventilation",
            "ECS",
            "Éclairage",
            "GTB/GTC",
            "Mise en place d'énergies renouvelables",
            "Autres travaux",
        ],
    },
    {
        "cle": "economie_energie_finale_pct",
        "libelle": "Économie d'énergie finale projetée (%)",
        "type": "pourcentage",
        "aide": "Gain attendu sur la consommation d'énergie finale du bâtiment, en %.",
    },
]
