"""Contenu du questionnaire : c'est ici qu'on modifie les questions et les réponses.

Les définitions des petits et grands travaux se trouvent dans contenu/definitions.md.
"""

# --------------------------------------------------------------------------
# Partie 1 : une réponse par bâtiment
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

# Réponses qui ouvrent la partie 2 pour le bâtiment.
STATUTS_DETAILLES = [OUI_PETITS, OUI_GRANDS]

# Réponse pré-sélectionnée quand « MOE » figure parmi les financements du bâtiment.
# Le répondant peut la modifier. Mettre None pour désactiver la pré-sélection.
STATUT_SI_MOE = OUI_GRANDS

# --------------------------------------------------------------------------
# Partie 2 : détails pour les bâtiments ayant répondu « Oui »
# --------------------------------------------------------------------------
# Chaque question devient une colonne du tableau de la partie 2.
#   cle          nom de la colonne dans l'export (sans espace ni accent)
#   libelle      titre de la colonne affiché au répondant
#   type         "choix" (liste déroulante), "texte", "nombre" ou "annee"
#   options      pour "choix" uniquement
#   aide         (facultatif) info-bulle sur la colonne
#   obligatoire  (facultatif) à remplir avant de pouvoir valider
#
# ⚠️ Questions d'exemple, à remplacer par les questions définitives.
QUESTIONS_PARTIE2 = [
    {
        "cle": "annee_fin_travaux",
        "libelle": "Année de fin des travaux",
        "type": "annee",
        "obligatoire": True,
    },
    {
        "cle": "nature_travaux",
        "libelle": "Nature principale des travaux",
        "type": "choix",
        "options": [
            "Isolation (murs, toiture, planchers)",
            "Menuiseries",
            "Chauffage / eau chaude",
            "Ventilation",
            "Éclairage",
            "Plusieurs postes",
            "Autre",
        ],
    },
    {
        "cle": "montant_ht",
        "libelle": "Montant des travaux (€ HT)",
        "type": "nombre",
    },
    {
        "cle": "precisions",
        "libelle": "Précisions",
        "type": "texte",
    },
]
