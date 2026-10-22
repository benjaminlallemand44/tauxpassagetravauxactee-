# Enquête : travaux de rénovation énergétique des bâtiments (maquette)

Maquette Streamlit d'une enquête auprès des collectivités sur les travaux de rénovation
énergétique de leurs bâtiments financés (SDIE, audit, MOE, AMO).

La page d'accueil liste les collectivités. Un clic ouvre le questionnaire de la collectivité,
qui ne montre **que ses bâtiments**, qu'elle en ait 1 ou 250. Il n'y a pas de code d'accès.
Chaque questionnaire a aussi un lien direct : `https://…/?structure=S0001`.

## Le questionnaire

**Onglet 1 – Situation des bâtiments.** Les définitions des petits et grands travaux
s'affichent, puis la question : *« Est-ce que les bâtiments suivants sont passés en travaux de
rénovation énergétique ? »*.

Le tableau montre d'abord les caractéristiques du bâtiment : nom, adresse, code postal,
commune, typologie, financements reçus. Viennent ensuite **cinq colonnes à cocher**, une par
réponse :

- Oui, en petits travaux
- Oui, en grands travaux de rénovation énergétique
- Non, mais je planifie de faire les travaux dans les 5 ans
- Non
- Ne sait pas

Une seule case peut être cochée par bâtiment : cocher une autre case remplace la première.
Quand **« MOE »** figure dans les financements, la case « Oui, en grands travaux » est
pré-cochée. La colonne RN n'est pas affichée, mais elle reste dans l'export.

**Onglet 2 – Détails des travaux.** Il liste uniquement les bâtiments enregistrés en « Oui,
petits » ou « Oui, grands » dans l'onglet 1. Pour chacun, on demande :

- **les travaux réalisés ou en cours**, en choix multiple (obligatoire) : isolation des murs,
  isolation du plancher, étanchéité à l'air, ouvrants, isolation des combles/toiture, système
  de chauffage, système de ventilation, ECS, éclairage, GTB/GTC, mise en place d'énergies
  renouvelables, autres travaux ;
- **l'économie d'énergie finale projetée**, en %.

On peut enregistrer à tout moment. La validation finale exige que l'onglet 1 soit complet et
que les questions obligatoires de l'onglet 2 soient remplies.

### Modifier le contenu

| Quoi | Où |
|---|---|
| Définitions des petits / grands travaux | `contenu/definitions.md` (Markdown) |
| Question, réponses, titres des colonnes à cocher, pré-sélection MOE, colonnes masquées | `enquete/questionnaire.py` |
| Questions de l'onglet 2 | `enquete/questionnaire.py`, liste `QUESTIONS_PARTIE2` |

## Administration : suivi et exports

Le bouton en bas de la page d'accueil, ou `https://…/?admin=1`, donne accès à :

- l'avancement par collectivité ;
- les réponses d'une collectivité ;
- l'export **Excel** ou **CSV**, avec une ligne par bâtiment : référentiel, réponse de
  l'onglet 1, détails de l'onglet 2, date de validation.

La page est ouverte à tous par défaut. Pour la protéger, définissez le secret
`ADMIN_PASSWORD` : sur Streamlit Cloud, dans **⋮ → Settings → Secrets**, ajoutez
`ADMIN_PASSWORD = "…"`.

## Stockage des réponses

Les réponses sont stockées dans un fichier SQLite (`data/reponses.db`, jamais poussé dans
Git). Sur Streamlit Community Cloud, ce fichier est **effacé à chaque redémarrage** de
l'application. Ça convient pour une maquette, mais pas pour une vraie collecte : il faudrait
alors une base externe.

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Les données de test sont fictives : 5 collectivités de 4, 5, 80, 250 et 100 bâtiments.

## Utiliser votre propre référentiel

Préparez un fichier Excel ou CSV (séparateur `;`) avec **une ligne par bâtiment** :

| Colonne | Obligatoire | Contenu |
|---|---|---|
| `id_structure` | oui | identifiant de la collectivité |
| `nom_structure` | oui | nom affiché |
| `email` | oui | adresse(s) de contact (plusieurs possibles, séparées par `,` ou `;`) |
| `nom_batiment` | oui | nom du bâtiment |
| `type_structure`, `id_batiment` | non | |
| `adresse`, `code_postal`, `commune`, `typologie`, `rn`, `financements`… | non | toutes les autres colonnes sont affichées, dans l'ordre du fichier, sauf celles masquées (`rn`) |

Puis lancez :

```bash
python preparer_donnees.py mon_referentiel.xlsx --base-url https://adresse-de-l-application
```

Le script écrit `data/structures.csv` et `data/batiments.csv`, lus par l'application. Il
produit aussi `data/acces.csv` et `data/brevo_contacts.csv`, qui contiennent le lien direct
de chaque collectivité, pour un éventuel envoi par e-mail.

## Tests

```bash
pip install pytest
python -m pytest
```

## Structure du dépôt

```
app.py                    interface Streamlit (accueil, questionnaire, administration)
enquete/questionnaire.py  question, réponses, pré-sélection MOE, questions de l'onglet 2
enquete/core.py           référentiel, stockage SQLite, exports
contenu/definitions.md    définitions des petits / grands travaux
preparer_donnees.py       référentiel -> fichiers de l'application + liens
generer_donnees_test.py   référentiel fictif de test
data/                     données de test fictives
tests/                    tests automatisés
```
