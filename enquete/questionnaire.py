"""Contenu du questionnaire : c'est ici qu'on modifie les textes, les questions et les réponses.

Les consignes de la partie 1 (définitions) se trouvent dans contenu/definitions.md.
"""

# --------------------------------------------------------------------------
# En-tête
# --------------------------------------------------------------------------
TITRE = "Enquête d'impact Travaux"
SOUS_TITRE = "Passage en travaux de rénovation énergétique à la suite du soutien ACTEE"
# {structure} est remplacé par le nom de la collectivité.
INTRODUCTION = (
    "Cette enquête porte sur les bâtiments de **{structure}**. Elle comporte deux parties ; "
    "la partie 1 est obligatoire et la partie 2 est recommandée ; vous pouvez enregistrer "
    "et revenir plus tard."
)
ONGLETS = ["Partie 1 : État des bâtiments", "Partie 2 : Détails des travaux"]

# --------------------------------------------------------------------------
# Partie 1 (obligatoire) : une réponse par bâtiment, une case à cocher par réponse
# --------------------------------------------------------------------------
QUESTION = (
    "Les bâtiments suivants sont-ils passés en travaux de rénovation énergétique depuis le "
    "soutien ACTEE (tous types de travaux, réalisés ou en cours) ?"
)

OUI_PETITS = "Oui, en « petits » travaux"
OUI_GRANDS = "Oui, en « grands » travaux de rénovation énergétique"
PREVUS = "Non, mais ma structure planifie d'effectuer les travaux dans les 5 ans"
STATUT_NON = "Non"
STATUTS = [OUI_PETITS, OUI_GRANDS, PREVUS, STATUT_NON, "Ne sait pas"]

# Titre de chaque colonne à cocher (le libellé complet de STATUTS s'affiche en info-bulle).
TITRES_COLONNES = {
    OUI_PETITS: "Oui, « petits »",
    OUI_GRANDS: "Oui, « grands »",
    PREVUS: "Prévus ≤ 5 ans",
    STATUT_NON: "Non",
    "Ne sait pas": "Ne sait pas",
}

# Réponses qui ouvrent la partie 2 pour le bâtiment.
STATUTS_DETAILLES = [OUI_PETITS, OUI_GRANDS]

# Réponse pré-cochée quand « MOE » figure parmi les financements du bâtiment.
# Le répondant peut la modifier. Mettre None pour désactiver la pré-sélection.
STATUT_SI_MOE = OUI_GRANDS

# Colonnes du référentiel qui ne sont pas montrées au répondant (elles restent dans l'export).
COLONNES_MASQUEES = {"rn", "code_postal"}

# --------------------------------------------------------------------------
# Partie 2 (recommandée) : détails pour les bâtiments ayant répondu « Oui »
# --------------------------------------------------------------------------
CONSIGNE_PARTIE2 = """**Consigne**

**Économie d'énergie finale projetée** : l'énergie finale est la quantité d'énergie consommée \
et facturée à son point d'utilisation, celle qui correspond à la facture d'énergie. Cette \
information figure dans les audits énergétiques ou les études de maîtrise d'œuvre (prendre \
la donnée la plus récente). Cette donnée est théorique.

**Acronymes** : ECS = Eau Chaude Sanitaire ; GTB = Gestion Technique du Bâtiment ; \
GTC = Gestion Technique Centralisée."""

# Définitions affichées sous la consigne de la partie 2 (le menu ne montre que les noms courts).
DEFINITIONS_MONTAGES = {
    "Maîtrise d'ouvrage déléguée": (
        "La collectivité confie une partie des attributions de la Maîtrise d'ouvrage à un "
        "tiers qui les exécute au nom et pour le compte de la collectivité."
    ),
    "Co-maîtrise d'ouvrage": (
        "Dans le cadre d'une opération menée conjointement par plusieurs collectivités, "
        "celles-ci confient l'exercice des attributions de la Maîtrise d'ouvrage à l'une "
        "d'entre elles."
    ),
    "Mutualisation des travaux avec plusieurs collectivités": (
        "Plusieurs collectivités mènent des travaux dans le cadre d'une opération unique."
    ),
    "Marché Global de Performance Énergétique": (
        "Réalisation de travaux avec objectif de performance énergétique dont l'atteinte "
        "conditionne la rémunération des entreprises (Contrat de Performance Énergétique)."
    ),
    "Marché Global de Performance Énergétique à Paiement Différé": (
        "Marché global de performance énergétique prévoyant également le pré-financement des "
        "travaux par le titulaire privé (cf. loi n° 2023-222 du 30 mars 2023)."
    ),
    "Marché de Partenariat": (
        "Forme de Contrat de Performance Énergétique impliquant, en plus d'un marché global, "
        "la délégation de la Maîtrise d'ouvrage au titulaire privé du marché, qui assure "
        "également le financement de l'opération."
    ),
    "Travaux en groupement de commandes": (
        "Plusieurs collectivités réalisent des travaux via la mise en place d'un groupement "
        "de commandes."
    ),
    "Marchés de travaux allotis": (
        "La collectivité fait réaliser les travaux via des marchés classiques, allotis au "
        "sens de l'ex-loi MOP, intégrée depuis 2019 dans le Code de la Commande Publique."
    ),
}

AUTRES_TRAVAUX = "Autres travaux"
AUTRE_MONTAGE = "Autre"

# Chaque question devient une colonne du tableau de la partie 2.
#   cle            nom de la colonne dans l'export (sans espace ni accent)
#   libelle        titre de la colonne affiché au répondant
#   type           "choix" (liste déroulante), "choix_multiple", "texte", "nombre",
#                  "pourcentage" ou "annee"
#   options        pour "choix" et "choix_multiple" (valeurs enregistrées dans l'export)
#   libelles       (facultatif) libellé affiché pour certaines options
#   aide           (facultatif) info-bulle sur la colonne
#   obligatoire    (facultatif) à remplir avant de pouvoir valider
#   requis_si      (facultatif) (cle, option) : à remplir si cette option est choisie
#   largeur        (facultatif) largeur de la colonne en pixels
QUESTIONS_PARTIE2 = [
    {
        "cle": "travaux",
        "libelle": "Travaux réalisés ou en cours",
        "type": "choix_multiple",
        "aide": "Plusieurs choix possibles.",
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
            "Protections solaires",
            "Brasseurs d'air",
            "Systèmes de climatisation",
            AUTRES_TRAVAUX,
        ],
        "libelles": {
            "ECS": "ECS (Eau Chaude Sanitaire)",
            "GTB/GTC": "GTB/GTC (Gestion Technique du Bâtiment / Centralisée)",
        },
        "largeur": 330,
    },
    {
        "cle": "autres_travaux_precision",
        "libelle": "Précisez (autres travaux)",
        "type": "texte",
        "aide": "À remplir uniquement si « Autres travaux » est coché.",
        "requis_si": ("travaux", AUTRES_TRAVAUX),
        "largeur": 170,
    },
    {
        "cle": "montage_contractuel",
        "libelle": "Montage contractuel",
        "type": "choix_multiple",
        "aide": "Plusieurs choix possibles. Définitions au-dessus du tableau.",
        "options": [
            "Maîtrise d'ouvrage déléguée",
            "Co-maîtrise d'ouvrage",
            "Mutualisation des travaux avec plusieurs collectivités",
            "Marché Global de Performance Énergétique",
            "Marché Global de Performance Énergétique à Paiement Différé",
            "Marché de Partenariat",
            "Travaux en groupement de commandes",
            "Marchés de travaux allotis",
            AUTRE_MONTAGE,
        ],
        "largeur": 280,
    },
    {
        "cle": "autre_montage_precision",
        "libelle": "Précisez (autre montage)",
        "type": "texte",
        "aide": "À remplir uniquement si « Autre » est coché dans le montage contractuel.",
        "requis_si": ("montage_contractuel", AUTRE_MONTAGE),
        "largeur": 170,
    },
    {
        "cle": "economie_energie_finale_pct",
        "libelle": "Économie d'énergie finale projetée (%)",
        "type": "pourcentage",
        "aide": "Énergie consommée et facturée au point d'utilisation (facture d'énergie). "
                "Donnée théorique issue de l'audit ou de l'étude de MOE la plus récente.",
    },
    {
        "cle": "commentaire_travaux",
        "libelle": "Commentaire",
        "type": "texte",
        "aide": "Difficultés rencontrées ou surmontées par votre structure, critères "
                "d'arbitrage ou de priorisation, aléas…",
    },
]
