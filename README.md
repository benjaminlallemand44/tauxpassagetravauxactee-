# Enquête d'impact Travaux (maquette)

Maquette Streamlit d'une enquête auprès des collectivités sur les travaux de rénovation
énergétique de leurs bâtiments financés (SDIE, audit, MOE, AMO).

La page d'accueil liste les collectivités. Un clic ouvre le questionnaire de la collectivité,
qui ne montre **que ses bâtiments**, qu'elle en ait 1 ou 250. Il n'y a pas de code d'accès.
Chaque questionnaire a aussi un lien direct : `https://…/?structure=S0001`.

## Le questionnaire

**Enquête d'impact Travaux**, sous-titrée « Passage en travaux de rénovation énergétique à la
suite du soutien ACTEE ». Elle comporte deux parties : la partie 1 est obligatoire, la
partie 2 est recommandée.

**Partie 1 : État des bâtiments.** La question posée est *« Les bâtiments suivants sont-ils
passés en travaux de rénovation énergétique depuis le soutien ACTEE (tous types de travaux,
réalisés ou en cours) ? »*. Elle est précédée d'une **Consigne** qui définit les « petits »
travaux, les « grands » travaux et les travaux prévus.

Le tableau montre les caractéristiques du bâtiment (nom, adresse, commune, typologie,
financements reçus), puis **cinq colonnes à cocher**, une seule par bâtiment :
- Oui, en « petits » travaux ;
- Oui, en « grands » travaux de rénovation énergétique ;
- Prévus ≤ 5 ans (non, mais la structure planifie d'effectuer les travaux dans les 5 ans) ;
- Non ;
- Ne sait pas.

Quand une **MOE** figure dans les financements, « Oui, « grands » » est pré-coché. Le RN et
le code postal ne sont pas affichés, mais restent dans l'export.

**Partie 2 : Détails des travaux.** Elle concerne les bâtiments enregistrés en « Oui » dans
la partie 1. Une consigne explique l'énergie finale et les acronymes, et un bloc dépliable
donne la définition des montages contractuels. Les colonnes demandées sont :
- **les travaux réalisés ou en cours**, en choix multiple : isolation des murs, du plancher,
  des combles/toiture, étanchéité à l'air, ouvrants, chauffage, ventilation, ECS, éclairage,
  GTB/GTC, énergies renouvelables, protections solaires, brasseurs d'air, climatisation,
  autres travaux ;
- **précisez (autres travaux)**, obligatoire si « Autres travaux » est coché ;
- **le montage contractuel**, en choix multiple : MOD, co-maîtrise d'ouvrage, mutualisation,
  MGPE, MGPE à paiement différé, marché de partenariat, groupement de commandes, marchés
  allotis, autre ;
- **précisez (autre montage)**, obligatoire si « Autre » est coché ;
- **l'économie d'énergie finale projetée**, en % ;
- **un commentaire** sur les difficultés, les arbitrages et les aléas.

On peut enregistrer à tout moment. Pour valider, il suffit que la partie 1 soit complète. Si
la partie 2 n'est pas remplie, l'application le signale sans bloquer la validation.

### Modifier le contenu

| Quoi | Où |
|---|---|
| Définitions des petits / grands travaux | `contenu/definitions.md` (Markdown) |
| Titre, sous-titre, introduction, noms des onglets | `enquete/questionnaire.py` |
| Question, réponses, titres des colonnes à cocher, pré-sélection MOE, colonnes masquées | `enquete/questionnaire.py` |
| Consigne de la partie 2, définitions des montages, questions de la partie 2 | `enquete/questionnaire.py` (`CONSIGNE_PARTIE2`, `DEFINITIONS_MONTAGES`, `QUESTIONS_PARTIE2`) |

## Administration : suivi et exports

Le bouton en bas de la page d'accueil, ou `https://…/?admin=1`, donne accès à :

- l'avancement par collectivité ;
- les réponses d'une collectivité ;
- l'export **Excel** ou **CSV**, avec une ligne par bâtiment : référentiel, réponse de
  la partie 1, détails de la partie 2, date de validation.

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
