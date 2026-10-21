# Enquête : travaux de rénovation énergétique des bâtiments

Application Streamlit pour interroger environ 1000 structures (communes, EPCI, départements,
bailleurs…) sur les travaux de rénovation énergétique de leurs bâtiments financés (SDIE, audit,
MOE, AMO).

Chaque structure ouvre **son lien personnel** et voit **exactement ses bâtiments**, qu'elle en
ait 1 ou 250, dans un tableau sans ligne vide.

## Le questionnaire

**Partie 1 – Situation des bâtiments.** Les définitions des petits et grands travaux s'affichent,
puis la question : *« Est-ce que les bâtiments suivants sont passés en travaux de rénovation
énergétique ? »*. Chaque bâtiment reçoit une réponse parmi :

- Oui, en petits travaux
- Oui, en grands travaux de rénovation énergétique
- Non, mais je planifie de faire les travaux dans les 5 ans
- Non
- Ne sait pas

Quand **« MOE »** figure dans les financements d'un bâtiment, la réponse « Oui, en grands
travaux » est **pré-sélectionnée**. Le répondant la vérifie et peut la corriger.

**Partie 2 – Détails des travaux.** Elle ne liste que les bâtiments marqués « Oui, en petits
travaux » ou « Oui, en grands travaux » en partie 1, pour poser des questions complémentaires.

On peut enregistrer à tout moment et revenir plus tard avec le même lien. La validation finale
exige que la partie 1 soit complète et que les questions obligatoires de la partie 2 soient
remplies.

### Modifier le contenu

| Quoi | Où |
|---|---|
| Définitions des petits / grands travaux | `contenu/definitions.md` (Markdown) |
| Question, réponses, réponse pré-sélectionnée si MOE | `enquete/questionnaire.py` |
| Questions de la partie 2 (⚠️ exemples à remplacer) | `enquete/questionnaire.py`, liste `QUESTIONS_PARTIE2` |

## Côté administrateur : récupérer les réponses

Ouvrez `https://…/?admin=1` et saisissez le mot de passe `ADMIN_PASSWORD`. La page affiche :

- l'avancement par structure : bâtiments renseignés, date de validation ;
- les réponses d'une structure, choisie dans une liste ;
- l'export **Excel** ou **CSV** de toutes les réponses, avec une ligne par bâtiment : référentiel,
  réponse de la partie 1, détails de la partie 2, date de validation.

Les réponses sont stockées dans `data/reponses.db` (SQLite). Ce fichier n'est jamais poussé dans
le dépôt. Pensez à le **sauvegarder régulièrement** pendant la collecte : faites un export Excel
ou copiez ce fichier.

## Lancer en local

```bash
pip install -r requirements.txt
export ADMIN_PASSWORD=mon-mot-de-passe        # Windows : set ADMIN_PASSWORD=mon-mot-de-passe
streamlit run app.py
```

Des données de test fictives sont fournies dans `data/` : 5 structures de 4, 5, 80, 250 et
100 bâtiments. La structure S0003 a deux contacts. Les liens de test se trouvent dans
`data/acces.csv`.

## Utiliser votre propre base

### 1. Le référentiel

Préparez un fichier Excel ou CSV (séparateur `;`) avec **une ligne par bâtiment** :

| Colonne | Obligatoire | Contenu |
|---|---|---|
| `id_structure` | oui | identifiant de la structure |
| `nom_structure` | oui | nom affiché au répondant |
| `email` | oui | adresse(s) de la structure, voir ci-dessous |
| `nom_batiment` | oui | nom du bâtiment |
| `type_structure`, `id_batiment` | non | |
| `adresse`, `code_postal`, `commune`, `typologie`, `rn`, `financements`… | non | **toutes les autres colonnes sont affichées** au répondant, dans l'ordre du fichier |

Les financements peuvent être donnés de deux façons :

- une colonne texte, par exemple `financements` = « Audit + MOE » ;
- des colonnes `sdie`, `audit`, `moe`, `amo` valant Oui ou Non.

La pré-sélection fonctionne dans les deux cas. Elle repère « MOE » ou « maîtrise d'œuvre » dans
toute colonne dont le nom contient « financ ».

**Plusieurs personnes pour une même structure** : mettez plusieurs adresses dans la cellule
`email`, séparées par `,` ou `;`. Vous pouvez aussi mettre des adresses différentes sur
différentes lignes de la même structure. **Tous les contacts d'une structure partagent le même
code d'accès** et répondent sur le même questionnaire.

### 2. Générer les codes et les liens

```bash
python preparer_donnees.py mon_referentiel.xlsx --base-url https://adresse-de-l-application
```

Le script écrit dans `data/` :

- `structures.csv` et `batiments.csv`, lus par l'application ;
- `acces.csv`, avec une ligne par contact : e-mail, structure, code, lien ;
- `brevo_contacts.csv`, le fichier à importer dans Brevo.

Si vous le relancez après une correction du référentiel, les codes déjà attribués sont conservés :
les liens déjà envoyés restent valables.

### 3. Envoyer la campagne avec Brevo

1. **Contacts → Paramètres → Attributs de contact** : créez les attributs texte `ID_STRUCTURE`,
   `NOM_STRUCTURE`, `CODE_ACCES` et `LIEN`, ainsi que l'attribut nombre `NB_BATIMENTS`.
2. **Contacts → Importer des contacts** : chargez `brevo_contacts.csv`, vérifiez que chaque
   colonne est associée au bon attribut, et rangez les contacts dans une nouvelle liste.
3. **Campagnes → Créer une campagne e-mail** : dans le message, insérez les champs
   personnalisés, par exemple :

   > Bonjour,
   > Dans le cadre de l'enquête sur la rénovation énergétique, merci de renseigner la situation
   > des {{ contact.NB_BATIMENTS }} bâtiments de {{ contact.NOM_STRUCTURE }} :
   > **{{ contact.LIEN }}**
   > Si le lien ne fonctionne pas, connectez-vous avec votre e-mail et le code
   > **{{ contact.CODE_ACCES }}**. Ce code est commun à toutes les personnes de votre structure.

4. Envoyez d'abord un test à votre adresse, puis à la liste. Pour les relances, ciblez les
   structures non validées : leur liste est visible dans la page d'administration.

⚠️ Dans Brevo, un contact (une adresse e-mail) n'a qu'**un seul** lien. Si une même adresse
est contact de plusieurs structures, le script vous prévient. Seule la première structure
figure alors dans `brevo_contacts.csv`, et il faudra envoyer les autres liens à part
(voir `acces.csv`).

> ⚠️ Les vrais fichiers contiennent des adresses e-mail et des codes d'accès. Ne les poussez pas
> dans un dépôt public : rendez le dépôt privé, ou placez les données hors du dépôt avec la
> variable `ENQUETE_DATA_DIR`.

## Configuration

| Variable | Rôle | Par défaut |
|---|---|---|
| `ADMIN_PASSWORD` | mot de passe de la page d'administration (ou `.streamlit/secrets.toml`) | aucun : page admin désactivée |
| `ENQUETE_DATA_DIR` | dossier du référentiel (`structures.csv`, `batiments.csv`) | `data/` |
| `ENQUETE_DB` | fichier SQLite des réponses | `data/reponses.db` |

## Hébergement : à décider avant l'envoi

Les réponses sont stockées dans un fichier SQLite. Il faut donc un hébergement avec **disque persistant** :

- **Serveur ou VM** (OVH, Scaleway, serveur interne…) : `streamlit run app.py` derrière un
  reverse proxy HTTPS. C'est la solution la plus simple avec le code actuel.
- **Streamlit Community Cloud** : très bien pour tester, mais ⚠️ le disque est effacé à chaque
  redémarrage, et les réponses seraient perdues. Pour la vraie collecte, il faudrait passer le
  stockage sur une base externe (PostgreSQL : Supabase, Neon…). Seules les fonctions de stockage
  de `enquete/core.py` sont à adapter.

Pensez au **RGPD** : mention d'information dans le mail, hébergement dans l'UE, durée de conservation.

## Tests

```bash
pip install pytest
python -m pytest
```

## Structure du dépôt

```
app.py                    interface Streamlit (répondant + administration)
enquete/questionnaire.py  question, réponses, pré-sélection MOE, questions de la partie 2
enquete/core.py           référentiel, identification, stockage SQLite, exports
contenu/definitions.md    définitions des petits / grands travaux
preparer_donnees.py       référentiel -> fichiers de l'application + liens + fichier Brevo
generer_donnees_test.py   référentiel fictif de test
data/                     données de test fictives
tests/                    tests automatisés
```
