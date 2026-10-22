"""Enquête sur les travaux de rénovation énergétique des bâtiments (maquette).

Page d'accueil : liste des collectivités ; un clic ouvre le questionnaire de la
collectivité (lien direct : ?structure=S0001), qui ne montre que ses bâtiments.
Administration : ?admin=1 (protégée par ADMIN_PASSWORD si ce secret est défini).

Lancement : streamlit run app.py
"""
from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

from enquete import core
from enquete.questionnaire import (QUESTION, QUESTIONS_PARTIE2, STATUT_NON, STATUT_SI_MOE,
                                   STATUTS, STATUTS_DETAILLES, TITRES_COLONNES)

st.set_page_config(page_title="Enquête rénovation énergétique", page_icon="🏢", layout="wide",
                   initial_sidebar_state="collapsed")

# Largeur (en pixels) des colonnes descriptives : les cases à cocher doivent rester visibles.
LARGEURS = {"adresse": 150, "code_postal": 70, "commune": 120, "typologie": 105,
            "financement": 110, "financements": 110}

# Une colonne à cocher par réponse possible de la partie 1.
CASES = {f"rep_{i}": statut for i, statut in enumerate(STATUTS)}


@st.cache_data
def referentiel() -> tuple[pd.DataFrame, pd.DataFrame]:
    return core.charger_structures(), core.charger_batiments()


def mot_de_passe_admin() -> str | None:
    """Variable d'environnement, sinon secret Streamlit (Settings > Secrets)."""
    if os.environ.get("ADMIN_PASSWORD"):
        return os.environ["ADMIN_PASSWORD"]
    try:
        return st.secrets.get("ADMIN_PASSWORD")
    except Exception:  # pas de fichier secrets.toml
        return None


def aller_a(**params: str) -> None:
    st.query_params.clear()
    st.query_params.update(params)


# --------------------------------------------------------------------------
# Accueil
# --------------------------------------------------------------------------
def page_accueil(structures: pd.DataFrame, batiments: pd.DataFrame) -> None:
    st.title("Enquête : travaux de rénovation énergétique")
    st.write("Choisissez une collectivité pour ouvrir son questionnaire.")

    synthese = core.avancement(core.chemin_base(), structures, batiments)
    recherche = st.text_input("Rechercher une collectivité", placeholder="Nom ou identifiant")
    if recherche:
        masque = (synthese["nom_structure"].str.contains(recherche, case=False, regex=False)
                  | synthese["id_structure"].str.contains(recherche, case=False, regex=False))
        synthese = synthese[masque]

    for _, s in synthese.iterrows():
        c1, c2, c3 = st.columns([5, 2, 2], vertical_alignment="center")
        c1.button(s["nom_structure"], key=f"ouvrir_{s['id_structure']}", width="stretch",
                  on_click=aller_a, kwargs={"structure": s["id_structure"]})
        c2.write(f"{s['nb_batiments']} bâtiment(s)")
        if s["valide_le"]:
            c3.write("✅ Validé")
        elif s["nb_renseignes"]:
            c3.write(f"✏️ {s['nb_renseignes']} / {s['nb_batiments']} renseignés")
        else:
            c3.write("Non commencé")
    if synthese.empty:
        st.info("Aucune collectivité ne correspond à cette recherche.")

    st.divider()
    st.button("Administration : suivi et exports", on_click=aller_a, kwargs={"admin": "1"})


# --------------------------------------------------------------------------
# Questionnaire
# --------------------------------------------------------------------------
def _colonne_question(q: dict):
    aide = q.get("aide")
    libelle = q["libelle"] + (" *" if q.get("obligatoire") else "")
    if q["type"] == "choix":
        return st.column_config.SelectboxColumn(libelle, options=q["options"], help=aide, width="medium")
    if q["type"] == "choix_multiple":
        return st.column_config.MultiselectColumn(libelle, options=q["options"], help=aide, width="large")
    if q["type"] == "annee":
        return st.column_config.NumberColumn(libelle, min_value=core.ANNEE_MIN,
                                             max_value=core.ANNEE_MAX, step=1, format="%d", help=aide)
    if q["type"] == "pourcentage":
        return st.column_config.NumberColumn(libelle, min_value=0, max_value=100, step=1,
                                             format="%d %%", help=aide, width="medium")
    if q["type"] == "nombre":
        return st.column_config.NumberColumn(libelle, min_value=0, help=aide)
    return st.column_config.TextColumn(libelle, help=aide, width="large")


def _erreurs(titre: str, erreurs: list[str]) -> bool:
    if erreurs:
        st.error(titre + "\n\n- " + "\n- ".join(erreurs))
    return bool(erreurs)


def _recharger(id_s: str, message: str | None = None) -> None:
    """Après un enregistrement : les tableaux sont reconstruits depuis la base."""
    st.session_state.pop(f"p1_base_{id_s}", None)
    st.session_state.pop(f"p1_avant_{id_s}", None)
    st.session_state[f"gen_{id_s}"] = st.session_state.get(f"gen_{id_s}", 0) + 1
    if message:
        st.session_state["message"] = message


def statuts_depuis_cases(df: pd.DataFrame) -> pd.Series:
    """Case cochée -> libellé de la réponse ("" si aucune case)."""
    cases = df[list(CASES)].fillna(False).astype(bool)
    return cases.apply(lambda ligne: next((CASES[c] for c in CASES if ligne[c]), ""), axis=1)


def base_partie1(tableau: pd.DataFrame, batiments: pd.DataFrame) -> pd.DataFrame:
    caracteristiques = core.colonnes_affichees(batiments)
    base = tableau[["id_batiment", *caracteristiques, "commentaire"]].copy()
    for cle, statut in CASES.items():
        base[cle] = tableau["statut"].eq(statut)
    return base[["id_batiment", *caracteristiques, *CASES, "commentaire"]]


def editeur_partie1(id_s: str, tableau: pd.DataFrame, batiments: pd.DataFrame) -> pd.DataFrame:
    """Tableau à cases : une seule case cochée par ligne. Cocher une deuxième case
    remplace la première (le tableau est alors corrigé puis réaffiché)."""
    cle_base = f"p1_base_{id_s}"
    if cle_base not in st.session_state:
        st.session_state[cle_base] = base_partie1(tableau, batiments)
    base = st.session_state[cle_base]
    caracteristiques = core.colonnes_affichees(batiments)

    config = {
        "id_batiment": None,
        "num": st.column_config.NumberColumn("N°", width=45, pinned=True),
        "nom_batiment": st.column_config.TextColumn("Bâtiment", width=180, pinned=True),
        "commentaire": st.column_config.TextColumn("Commentaire", width="medium"),
        **{c: st.column_config.TextColumn(core.libelle(c), width=LARGEURS.get(c, "medium"))
           for c in caracteristiques if c not in ("num", "nom_batiment")},
        **{cle: st.column_config.CheckboxColumn(TITRES_COLONNES.get(statut, statut), help=statut,
                                                width=112)
           for cle, statut in CASES.items()},
    }
    edite = st.data_editor(
        base, key=f"p1_{id_s}_{st.session_state.get(f'gen_{id_s}', 0)}",
        hide_index=True, num_rows="fixed", width="stretch", placeholder="",
        # Hauteur pleine : pas de défilement interne, la page défile normalement.
        height=38 + 35 * len(base),
        disabled=caracteristiques, column_config=config,
    )

    # Comparaison avec l'état affiché juste avant ce clic, pour savoir quelle case est nouvelle.
    cle_avant = f"p1_avant_{id_s}"
    avant = st.session_state.get(cle_avant, base[list(CASES)])
    corrigees = core.une_seule_case(edite[list(CASES)], avant)
    st.session_state[cle_avant] = edite[list(CASES)] if corrigees is None else corrigees
    if corrigees is not None:
        st.session_state[cle_base] = edite.assign(**corrigees)
        st.session_state[f"gen_{id_s}"] = st.session_state.get(f"gen_{id_s}", 0) + 1
        st.rerun()
    return edite.assign(statut=statuts_depuis_cases(edite))


def editeur_partie2(id_s: str, details: pd.DataFrame) -> pd.DataFrame:
    cles = [q["cle"] for q in QUESTIONS_PARTIE2]
    donnees = details[["id_batiment", "num", "nom_batiment", "statut", *cles]].copy()
    for q in QUESTIONS_PARTIE2:
        if q["type"] == "choix_multiple":
            donnees[q["cle"]] = donnees[q["cle"]].map(core._liste)
        elif q["type"] in ("nombre", "annee", "pourcentage"):
            donnees[q["cle"]] = pd.to_numeric(donnees[q["cle"]], errors="coerce")
        else:
            donnees[q["cle"]] = donnees[q["cle"]].astype(object).where(donnees[q["cle"]].notna(), None)
    config = {
        "id_batiment": None,
        "num": st.column_config.NumberColumn("N°", width="small", pinned=True),
        "nom_batiment": st.column_config.TextColumn("Bâtiment", pinned=True),
        "statut": st.column_config.TextColumn("Réponse (partie 1)"),
        **{q["cle"]: _colonne_question(q) for q in QUESTIONS_PARTIE2},
    }
    return st.data_editor(
        donnees, key=f"p2_{id_s}_{st.session_state.get(f'gen_{id_s}', 0)}",
        hide_index=True, num_rows="fixed", width="stretch", placeholder="",
        height=38 + 35 * len(donnees),
        disabled=["num", "nom_batiment", "statut"], column_config=config,
    )


def page_questionnaire(structure: dict, batiments: pd.DataFrame) -> None:
    db = core.chemin_base()
    id_s = structure["id_structure"]

    st.button("← Toutes les collectivités", on_click=aller_a)
    st.title("Travaux de rénovation énergétique")
    st.write(f"Cette enquête porte sur les bâtiments de **{structure['nom_structure']}**. "
             "Elle comporte deux parties ; vous pouvez enregistrer et revenir plus tard.")

    tableau = core.tableau_structure(db, id_s, batiments)
    details = core.tableau_details(db, id_s, batiments)
    valide_le = core.date_validation(db, id_s)

    c1, c2, c3 = st.columns(3)
    c1.metric("Bâtiments", len(tableau))
    c2.metric("Bâtiments avec travaux (partie 2)", len(details))
    c3.metric("Statut", "Validé" if valide_le else "En cours de saisie")

    # Toujours présente, même vide : la mise en page au-dessus des onglets ne bouge pas.
    zone_messages = st.container()
    if message := st.session_state.pop("message", None):
        zone_messages.success(message)
    if valide_le:
        zone_messages.info(f"Questionnaire validé le {valide_le.replace('T', ' à ')}. "
                           "Vous pouvez encore modifier vos réponses.")

    # La clé fait retenir l'onglet ouvert d'un rafraîchissement à l'autre.
    onglet1, onglet2 = st.tabs(["1. Situation des bâtiments", "2. Détails des travaux"],
                               key=f"onglets_{id_s}", on_change="rerun")

    with onglet1:
        st.subheader(QUESTION)
        if definitions := core.charger_definitions():
            st.info(definitions)
        st.caption("Cochez une case par bâtiment.")
        if tableau["pre_rempli"].any():
            st.caption(f"Pour les bâtiments ayant bénéficié d'une MOE, la case « {STATUT_SI_MOE} » "
                       "est pré-cochée : vérifiez-la et corrigez-la si besoin.")
        edite1 = editeur_partie1(id_s, tableau, batiments)
        manquants = int(edite1["statut"].eq("").sum())
        st.caption(f"{len(edite1) - manquants} / {len(edite1)} bâtiment(s) renseigné(s).")
        b1, b2 = st.columns(2)
        if b1.button("💾 Enregistrer la partie 1", type="primary", width="stretch"):
            core.enregistrer_reponses(db, id_s, edite1, batiments)
            _recharger(id_s, "Partie 1 enregistrée.")
            st.rerun()
        if b2.button(f"Cocher « {STATUT_NON} » pour les bâtiments non renseignés", width="stretch"):
            vides = edite1["statut"].eq("")
            core.enregistrer_reponses(db, id_s, edite1.assign(
                statut=edite1["statut"].mask(vides, STATUT_NON)), batiments)
            _recharger(id_s, f"« {STATUT_NON} » coché pour {int(vides.sum())} bâtiment(s).")
            st.rerun()

    edite2 = None
    with onglet2:
        st.subheader("Détails des travaux")
        if details.empty:
            st.info("Aucun bâtiment concerné pour l'instant. Cette partie liste les bâtiments "
                    f"pour lesquels vous avez répondu « {' » ou « '.join(STATUTS_DETAILLES)} » "
                    "dans la partie 1, une fois celle-ci enregistrée.")
        else:
            st.write("Pour chacun des bâtiments ayant fait l'objet de travaux, merci de préciser :")
            if any(q.get("obligatoire") for q in QUESTIONS_PARTIE2):
                st.caption("Les colonnes marquées d'un astérisque (*) sont obligatoires pour valider.")
            edite2 = editeur_partie2(id_s, details)
            if st.button("💾 Enregistrer la partie 2", type="primary"):
                if not _erreurs("Corrigez les saisies suivantes :", core.verifier_details(edite2)):
                    core.enregistrer_details(db, id_s, edite2, batiments)
                    _recharger(id_s, "Partie 2 enregistrée.")
                    st.rerun()

    st.divider()
    if st.button("✅ Valider le questionnaire", width="stretch"):
        if edite2 is not None and _erreurs("Corrigez les saisies suivantes :",
                                           core.verifier_details(edite2)):
            return
        core.enregistrer_reponses(db, id_s, edite1, batiments)
        if edite2 is not None:
            core.enregistrer_details(db, id_s, edite2, batiments)
        _recharger(id_s)
        if manquants:
            st.error(f"Réponses enregistrées. Partie 1 : {manquants} bâtiment(s) sans réponse, "
                     "à compléter avant de valider.")
            return
        # La partie 2 est relue après enregistrement : de nouveaux « Oui » peuvent y être apparus.
        a_completer = core.verifier_details(core.tableau_details(db, id_s, batiments), complet=True)
        if _erreurs("Réponses enregistrées. Partie 2 à compléter avant de valider :", a_completer):
            return
        core.valider(db, id_s)
        st.session_state["message"] = "Merci ! Votre questionnaire est validé."
        st.rerun()


# --------------------------------------------------------------------------
# Administration
# --------------------------------------------------------------------------
def vers_excel(feuilles: dict[str, pd.DataFrame]) -> bytes:
    tampon = io.BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as writer:
        for nom, df in feuilles.items():
            df.to_excel(writer, sheet_name=nom, index=False)
    return tampon.getvalue()


def page_admin(structures: pd.DataFrame, batiments: pd.DataFrame) -> None:
    st.button("← Toutes les collectivités", on_click=aller_a)
    st.title("Administration de l'enquête")
    attendu = mot_de_passe_admin()
    if attendu and not st.session_state.get("admin"):
        with st.form("connexion_admin"):
            saisi = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                if core.egal(saisi, attendu):
                    st.session_state["admin"] = True
                    st.rerun()
                st.error("Mot de passe incorrect.")
        return

    db = core.chemin_base()
    synthese = core.avancement(db, structures, batiments)
    export = core.export_complet(db, structures, batiments)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Structures", len(synthese))
    c2.metric("Ayant commencé", int((synthese["nb_renseignes"] > 0).sum()))
    c3.metric("Validées", int(synthese["valide_le"].ne("").sum()))
    c4.metric("Bâtiments renseignés", f"{int(synthese['nb_renseignes'].sum())} / {len(batiments)}")

    st.subheader("Avancement par structure")
    st.dataframe(
        synthese, hide_index=True, width="stretch",
        column_config={"avancement_%": st.column_config.ProgressColumn(
            "Avancement", min_value=0, max_value=100, format="%d %%")},
    )

    st.subheader("Réponses d'une structure")
    choix = st.selectbox(
        "Structure", synthese["id_structure"],
        format_func=lambda i: f"{i} – {synthese.set_index('id_structure').loc[i, 'nom_structure']}")
    vue = export[export["id_structure"] == choix].drop(columns=["email"])
    en_tete = ["num", "nom_batiment", "statut", "commentaire", *[q["cle"] for q in QUESTIONS_PARTIE2]]
    st.dataframe(vue[en_tete + [c for c in vue.columns if c not in en_tete]],
                 hide_index=True, width="stretch")

    st.subheader("Exports (une ligne par bâtiment)")
    d1, d2 = st.columns(2)
    d1.download_button(
        "Télécharger en Excel",
        vers_excel({"Reponses": export, "Avancement": synthese}),
        file_name="enquete_renovation_reponses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    d2.download_button(
        "Télécharger en CSV",
        export.to_csv(sep=";", index=False).encode("utf-8-sig"),
        file_name="enquete_renovation_reponses.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------
def main() -> None:
    structures, batiments = referentiel()
    id_structure = st.query_params.get("structure")
    if st.query_params.get("admin"):
        page_admin(structures, batiments)
    elif id_structure:
        trouvee = structures[structures["id_structure"] == id_structure]
        if trouvee.empty:
            st.error(f"Collectivité « {id_structure} » introuvable.")
            st.button("← Toutes les collectivités", on_click=aller_a)
        else:
            page_questionnaire(trouvee.iloc[0].to_dict(), batiments)
    else:
        page_accueil(structures, batiments)


main()
