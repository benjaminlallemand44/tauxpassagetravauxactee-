"""Enquête sur les travaux de rénovation énergétique des bâtiments.

Chaque structure accède à son questionnaire par son lien personnel (?code=XXXX)
ou avec son e-mail et son code d'accès, et ne voit que ses propres bâtiments.
Administration : ?admin=1 (mot de passe ADMIN_PASSWORD).

Lancement : streamlit run app.py
"""
from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

from enquete import core
from enquete.questionnaire import (QUESTION, QUESTIONS_PARTIE2, STATUT_NON, STATUT_SI_MOE,
                                   STATUTS, STATUTS_DETAILLES)

st.set_page_config(page_title="Enquête rénovation énergétique", page_icon="🏢", layout="wide")


@st.cache_data
def referentiel() -> tuple[pd.DataFrame, pd.DataFrame]:
    return core.charger_structures(), core.charger_batiments()


def secret(nom: str) -> str | None:
    """Variable d'environnement, sinon secret Streamlit (Settings > Secrets)."""
    if os.environ.get(nom):
        return os.environ[nom]
    try:
        return st.secrets.get(nom)
    except Exception:  # pas de fichier secrets.toml
        return None


def mot_de_passe_admin() -> str | None:
    return secret("ADMIN_PASSWORD")


# La couche de stockage lit DATABASE_URL dans l'environnement.
if (url_base := secret("DATABASE_URL")) and not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = url_base


def se_deconnecter() -> None:
    for cle in list(st.session_state.keys()):
        del st.session_state[cle]
    st.query_params.clear()


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------
def page_connexion(structures: pd.DataFrame) -> None:
    st.title("Enquête : travaux de rénovation énergétique")
    code_lien = st.query_params.get("code")
    if code_lien:
        structure = core.identifier_par_code(structures, code_lien)
        if structure:
            st.session_state["structure"] = structure
            st.rerun()
        st.error("Ce lien n'est pas valide. Vérifiez-le ou connectez-vous avec votre e-mail et votre code.")

    st.write(
        "Utilisez le lien personnel reçu par e-mail, ou saisissez ci-dessous "
        "votre adresse e-mail et le code d'accès indiqué dans ce message (le code est commun "
        "à toutes les personnes d'une même structure)."
    )
    with st.form("connexion"):
        email = st.text_input("Adresse e-mail")
        code = st.text_input("Code d'accès", type="password")
        if st.form_submit_button("Accéder au questionnaire", type="primary"):
            structure = core.identifier_par_email(structures, email, code)
            if structure:
                st.session_state["structure"] = structure
                st.rerun()
            st.error("E-mail ou code d'accès incorrect.")


# --------------------------------------------------------------------------
# Questionnaire
# --------------------------------------------------------------------------
def _colonne_question(q: dict):
    aide = q.get("aide")
    libelle = q["libelle"] + (" *" if q.get("obligatoire") else "")
    if q["type"] == "choix":
        return st.column_config.SelectboxColumn(libelle, options=q["options"], help=aide, width="medium")
    if q["type"] == "annee":
        return st.column_config.NumberColumn(libelle, min_value=core.ANNEE_MIN,
                                             max_value=core.ANNEE_MAX, step=1, format="%d", help=aide)
    if q["type"] == "nombre":
        return st.column_config.NumberColumn(libelle, min_value=0, help=aide)
    return st.column_config.TextColumn(libelle, help=aide, width="large")


def _nouvelle_version() -> None:
    """Nouvelles clés d'éditeurs : les tableaux sont rechargés depuis la base."""
    st.session_state["version"] = st.session_state.get("version", 0) + 1


def _erreurs(titre: str, erreurs: list[str]) -> bool:
    if erreurs:
        st.error(titre + "\n\n- " + "\n- ".join(erreurs))
    return bool(erreurs)


def editeur_partie1(tableau: pd.DataFrame, batiments: pd.DataFrame, cle: str) -> pd.DataFrame:
    # La réponse vient juste après le nom du bâtiment, pour rester visible sans défilement.
    reference = [c for c in core.colonnes_affichees(batiments) if c not in ("num", "nom_batiment")]
    colonnes = ["id_batiment", "num", "nom_batiment", "statut", "commentaire", *reference]
    config = {
        "id_batiment": None,
        "num": st.column_config.NumberColumn("N°", width="small", pinned=True),
        "nom_batiment": st.column_config.TextColumn("Bâtiment", pinned=True),
        "statut": st.column_config.SelectboxColumn(
            "Réponse", options=STATUTS, width="large", help=QUESTION),
        "commentaire": st.column_config.TextColumn("Commentaire", width="medium"),
    }
    for c in reference:
        config[c] = st.column_config.TextColumn(core.libelle(c))
    if tableau["pre_rempli"].any():
        colonnes.insert(colonnes.index("commentaire") + 1, "pre_rempli")
        config["pre_rempli"] = st.column_config.CheckboxColumn(
            "Pré-sélectionné (MOE)", width="small",
            help="Réponse proposée car une MOE a été financée sur ce bâtiment. À vérifier.")
    donnees = tableau[colonnes].copy()
    donnees["statut"] = donnees["statut"].replace("", None)
    return st.data_editor(
        donnees, key=cle, hide_index=True, num_rows="fixed", width="stretch",
        height=min(38 + 35 * len(donnees), 600),
        disabled=[c for c in colonnes if c not in ("statut", "commentaire")],
        column_config=config,
    )


def editeur_partie2(details: pd.DataFrame, cle: str) -> pd.DataFrame:
    cles = [q["cle"] for q in QUESTIONS_PARTIE2]
    donnees = details[["id_batiment", "num", "nom_batiment", "statut", *cles]].copy()
    for q in QUESTIONS_PARTIE2:
        if q["type"] in ("nombre", "annee"):
            donnees[q["cle"]] = pd.to_numeric(donnees[q["cle"]], errors="coerce")
        else:
            donnees[q["cle"]] = donnees[q["cle"]].astype(object).where(donnees[q["cle"]].notna(), None)
    config = {
        "id_batiment": None,
        "num": st.column_config.NumberColumn("N°", width="small"),
        "nom_batiment": st.column_config.TextColumn("Bâtiment"),
        "statut": st.column_config.TextColumn("Réponse (partie 1)"),
        **{q["cle"]: _colonne_question(q) for q in QUESTIONS_PARTIE2},
    }
    return st.data_editor(
        donnees, key=cle, hide_index=True, num_rows="fixed", width="stretch",
        height=min(38 + 35 * len(donnees), 600),
        disabled=["num", "nom_batiment", "statut"], column_config=config,
    )


def page_questionnaire(structure: dict, batiments: pd.DataFrame) -> None:
    db = core.chemin_base()
    id_s = structure["id_structure"]
    version = st.session_state.get("version", 0)

    with st.sidebar:
        st.markdown(f"**{structure['nom_structure']}**")
        st.button("Se déconnecter", on_click=se_deconnecter)

    st.title("Travaux de rénovation énergétique")
    st.write(f"Cette enquête porte sur les bâtiments de **{structure['nom_structure']}**. "
             "Elle comporte deux parties ; vous pouvez enregistrer et revenir plus tard "
             "avec le même lien.")

    tableau = core.tableau_structure(db, id_s, batiments)
    details = core.tableau_details(db, id_s, batiments)
    nb = len(tableau)
    nb_renseignes = int(tableau["statut"].ne("").sum())
    valide_le = core.date_validation(db, id_s)

    c1, c2, c3 = st.columns(3)
    c1.metric("Bâtiments", nb)
    c2.metric("Partie 1 renseignée", f"{nb_renseignes} / {nb}")
    c3.metric("Statut", "Validé" if valide_le else "En cours de saisie")

    if message := st.session_state.pop("message", None):
        st.success(message)
    if valide_le:
        st.info(f"Questionnaire validé le {valide_le.replace('T', ' à ')}. "
                "Vous pouvez encore modifier vos réponses avec le même lien.")

    onglet1, onglet2 = st.tabs(["1. Situation des bâtiments",
                                f"2. Détails des travaux ({len(details)} bâtiment(s))"])

    with onglet1:
        st.subheader(QUESTION)
        if definitions := core.charger_definitions():
            st.info(definitions)
        if tableau["pre_rempli"].any():
            st.caption(f"Pour les bâtiments ayant bénéficié d'une MOE, la réponse « {STATUT_SI_MOE} » "
                       "est pré-sélectionnée : vérifiez-la et corrigez-la si besoin.")
        edite1 = editeur_partie1(tableau, batiments, f"p1_{id_s}_{version}")
        b1, b2 = st.columns(2)
        if b1.button("💾 Enregistrer la partie 1", type="primary", width="stretch"):
            if not _erreurs("Corrigez les saisies suivantes :", core.verifier_reponses(edite1)):
                core.enregistrer_reponses(db, id_s, edite1, batiments)
                _nouvelle_version()
                st.session_state["message"] = "Partie 1 enregistrée."
                st.rerun()
        if b2.button(f"Mettre « {STATUT_NON} » sur les bâtiments non renseignés", width="stretch"):
            edite1 = edite1.copy()
            vides = edite1["statut"].fillna("").eq("")
            edite1.loc[vides, "statut"] = STATUT_NON
            if not _erreurs("Corrigez les saisies suivantes :", core.verifier_reponses(edite1)):
                core.enregistrer_reponses(db, id_s, edite1, batiments)
                _nouvelle_version()
                st.session_state["message"] = f"« {STATUT_NON} » appliqué à {int(vides.sum())} bâtiment(s)."
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
                st.caption("* réponse obligatoire pour valider le questionnaire.")
            edite2 = editeur_partie2(details, f"p2_{id_s}_{version}")
            if st.button("💾 Enregistrer la partie 2", type="primary"):
                if not _erreurs("Corrigez les saisies suivantes :", core.verifier_details(edite2)):
                    core.enregistrer_details(db, id_s, edite2, batiments)
                    _nouvelle_version()
                    st.session_state["message"] = "Partie 2 enregistrée."
                    st.rerun()

    st.divider()
    if st.button("✅ Valider le questionnaire", width="stretch"):
        erreurs = core.verifier_reponses(edite1)
        if edite2 is not None:
            erreurs += core.verifier_details(edite2)
        if _erreurs("Corrigez les saisies suivantes :", erreurs):
            return
        core.enregistrer_reponses(db, id_s, edite1, batiments)
        if edite2 is not None:
            core.enregistrer_details(db, id_s, edite2, batiments)
        _nouvelle_version()
        manquants = int(edite1["statut"].fillna("").eq("").sum())
        if manquants:
            st.session_state["message"] = "Réponses enregistrées."
            st.error(f"Partie 1 : {manquants} bâtiment(s) sans réponse. Complétez-les avant de valider.")
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
    st.title("Administration de l'enquête")
    attendu = mot_de_passe_admin()
    if not attendu:
        st.error("Aucun mot de passe administrateur n'est configuré (variable ADMIN_PASSWORD).")
        return
    if not st.session_state.get("admin"):
        with st.form("connexion_admin"):
            saisi = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                if core._egal(saisi, attendu):
                    st.session_state["admin"] = True
                    st.rerun()
                st.error("Mot de passe incorrect.")
        return

    db = core.chemin_base()
    if isinstance(db, str):
        st.caption("Stockage des réponses : base PostgreSQL externe (DATABASE_URL).")
    else:
        st.warning("Stockage des réponses : fichier local. Sur Streamlit Community Cloud, il est "
                   "effacé à chaque redémarrage : renseignez DATABASE_URL avant la vraie collecte.")
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
    st.button("Se déconnecter", on_click=se_deconnecter)


# --------------------------------------------------------------------------
def main() -> None:
    structures, batiments = referentiel()
    if st.query_params.get("admin"):
        page_admin(structures, batiments)
    elif "structure" in st.session_state:
        page_questionnaire(st.session_state["structure"], batiments)
    else:
        page_connexion(structures)


main()
