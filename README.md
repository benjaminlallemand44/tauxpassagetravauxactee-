# Enquête : travaux de rénovation énergétique des bâtiments

Application Streamlit pour interroger environ 1000 structures (communes, EPCI, départements,
bailleurs…) sur les travaux de rénovation énergétique de leurs bâtiments ayant bénéficié
d'un financement (SDIE, audit, MOE, AMO).

Chaque structure ouvre **son lien personnel** et voit **exactement ses bâtiments**, qu'elle en
ait 1 ou 250, dans un tableau avec une ligne par bâtiment, sans ligne vide. C'est ce qui manquait à
Sphinx Declic, où une question tableau a un nombre de lignes fixe.

## Côté répondant

- Accès par le lien personnel `https://…/?code=XXXXXXXX`, ou par e-mail + code d'accès.
- Tableau pré-rempli : n°, nom du bâtiment, commune, financements obtenus.
- Pour chaque bâtiment : **Travaux ?** (Oui – réalisés / En cours / Prévus / Non / Ne sait pas),
  type de travaux, année, commentaire.
- Bouton « Mettre « Non » sur les bâtiments non renseignés », pratique pour les grosses structures.
- Enregistrement à tout moment : on peut revenir plus tard avec le même lien.
- Validation finale, possible uniquement quand tous les bâtiments sont renseignés. Les réponses
  restent modifiables après la validation.

## Côté administrateur

`https://…/?admin=1` avec le mot de passe `ADMIN_PASSWORD` :

- avancement par structure (bâtiments renseignés, date de validation) ;
- export **Excel** ou **CSV** avec une ligne par bâtiment : référentiel, réponse et validation.

## Lancer en local

```bash
pip install -r requirements.txt
export ADMIN_PASSWORD=mon-mot-de-passe        # Windows : set ADMIN_PASSWORD=mon-mot-de-passe
streamlit run app.py
```

Des données de test fictives sont fournies dans `data/` : 5 structures de 4, 5, 80, 250 et
100 bâtiments. Les liens de test se trouvent dans `data/acces.csv`, colonne `lien`.

## Utiliser votre propre base

1. Préparez un fichier Excel ou CSV (séparateur `;`) avec **une ligne par bâtiment** :

   | Colonne | Obligatoire | Contenu |
   |---|---|---|
   | `id_structure` | oui | identifiant de la structure |
   | `nom_structure` | oui | nom affiché au répondant |
   | `email` | oui | adresse du destinataire (une seule par structure) |
   | `nom_batiment` | oui | nom du bâtiment |
   | `type_structure`, `id_batiment`, `commune`, `surface_m2`, `annee_construction` | non | |
   | `sdie`, `audit`, `moe`, `amo` | non | Oui / Non |

2. Générez les fichiers de l'application et les liens personnels :

   ```bash
   python preparer_donnees.py mon_referentiel.xlsx --base-url https://adresse-de-l-application
   ```

   Le script écrit `data/structures.csv`, `data/batiments.csv` et `data/acces.csv`. Ce dernier
   contient e-mail, code et lien de chaque structure, à utiliser pour le publipostage.
   Si vous le relancez après une correction du référentiel, les codes déjà attribués sont
   conservés : les liens déjà envoyés restent valables.

3. Envoyez les liens par publipostage depuis votre messagerie (Outlook, Thunderbird…),
   avec la colonne `lien` comme champ de fusion.

> ⚠️ Les vrais fichiers contiennent des adresses e-mail et des codes d'accès. Ne les poussez
> pas dans un dépôt public : rendez le dépôt privé, ou placez les données hors du dépôt avec
> la variable `ENQUETE_DATA_DIR`.

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
- **Streamlit Community Cloud** : ⚠️ le disque est effacé à chaque redémarrage, et les réponses
  seraient perdues. Il faudrait passer le stockage sur une base externe (PostgreSQL : Supabase,
  Neon…). Seules les fonctions de stockage de `enquete/core.py` sont à adapter.

Pensez au **RGPD** : mention d'information dans le mail, hébergement dans l'UE, durée de conservation.

## Tests

```bash
pip install pytest
python -m pytest
```

Les tests couvrent l'identification, l'isolation entre structures, l'enregistrement, la
validation, l'export, la préparation des données, et l'interface (via `streamlit.testing`).

## Structure du dépôt

```
app.py                    interface Streamlit (répondant + administration)
enquete/core.py           référentiel, identification, stockage SQLite, exports
preparer_donnees.py       référentiel -> fichiers de l'application + liens personnels
generer_donnees_test.py   référentiel fictif de test
data/                     données de test fictives
tests/                    tests automatisés
```
