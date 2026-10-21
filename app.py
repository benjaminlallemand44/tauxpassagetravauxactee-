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

st.set_page_config(page_title="Enquête rénovation énergétique", page_icon="🏢", layout="wide")

COLONNES_REFERENTIEL = ["num", "nom_batiment", "commune", "financement"]
COLONNES_REPONSE = ["statut", "type_travaux", "annee", "commentaire"]


@st.cache_data
def referentiel() -> tuple[pd.DataFrame, pd.DataFrame]:
    return core.charger_structures(), core.charger_batiments()


def mot_de_passe_admin() -> str | None:
    if os.environ.get("ADMIN_PASSWORD"):
        return os.environ["ADMIN_PASSWORD"]
    try:
        return st.secrets.get("ADMIN_PASSWORD")
    except Exception:  # pas de fichier secrets.toml
        return None


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
        "votre adresse e-mail et le code d'accès indiqué dans ce message."
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
def _enregistrer(edite: pd.DataFrame, id_structure: str, batiments: pd.DataFrame) -> bool:
    erreurs = core.verifier_reponses(edite)
    if erreurs:
        st.error("Corrigez les saisies suivantes avant d'enregistrer :\n\n- " + "\n- ".join(erreurs))
        return False
    core.enregistrer_reponses(core.chemin_base(), id_structure, edite, batiments)
    # Nouvelle clé d'éditeur : le tableau est rechargé depuis la base.
    st.session_state["version"] = st.session_state.get("version", 0) + 1
    return True


def page_questionnaire(structure: dict, batiments: pd.DataFrame) -> None:
    db = core.chemin_base()
    id_s = structure["id_structure"]

    with st.sidebar:
        st.markdown(f"**{structure['nom_structure']}**  \n{structure['email']}")
        st.button("Se déconnecter", on_click=se_deconnecter)

    st.title("Travaux de rénovation énergétique")
    st.write(
        f"Voici les bâtiments de **{structure['nom_structure']}** ayant bénéficié d'un "
        "financement (SDIE, audit énergétique, maîtrise d'œuvre ou AMO). Pour chacun, indiquez "
        "si des travaux de rénovation énergétique ont été réalisés, sont en cours ou sont prévus."
    )

    tableau = core.tableau_structure(db, id_s, batiments)
    nb = len(tableau)
    nb_renseignes = int(tableau["statut"].ne("").sum())
    valide_le = core.date_validation(db, id_s)

    c1, c2, c3 = st.columns(3)
    c1.metric("Bâtiments", nb)
    c2.metric("Renseignés", f"{nb_renseignes} / {nb}")
    c3.metric("Statut", "Validé" if valide_le else "En cours de saisie")
    st.progress(nb_renseignes / nb if nb else 0.0)

    if message := st.session_state.pop("message", None):
        st.success(message)
    if valide_le:
        st.info(f"Questionnaire validé le {valide_le.replace('T', ' à ')}. "
                "Vous pouvez encore modifier vos réponses avec le même lien.")

    st.caption("Type de travaux et année : à renseigner si les travaux sont réalisés, en cours ou prévus. "
               "Pensez à enregistrer régulièrement ; vous pouvez revenir plus tard avec le même lien.")

    donnees = tableau[["id_batiment", *COLONNES_REFERENTIEL, *COLONNES_REPONSE]].copy()
    for col in ["statut", "type_travaux"]:
        donnees[col] = donnees[col].replace("", None)

    edite = st.data_editor(
        donnees,
        key=f"editeur_{id_s}_{st.session_state.get('version', 0)}",
        hide_index=True,
        num_rows="fixed",
        use_container_width=True,
        height=min(38 + 35 * nb, 700),
        disabled=COLONNES_REFERENTIEL,
        column_config={
            "id_batiment": None,
            "num": st.column_config.NumberColumn("N°", width="small"),
            "nom_batiment": st.column_config.TextColumn("Bâtiment", width="medium"),
            "commune": st.column_config.TextColumn("Commune"),
            "financement": st.column_config.TextColumn("Financé"),
            "statut": st.column_config.SelectboxColumn(
                "Travaux ?", options=core.STATUTS, width="medium",
                help="Des travaux de rénovation énergétique ont-ils été réalisés sur ce bâtiment ?"),
            "type_travaux": st.column_config.SelectboxColumn(
                "Type de travaux", options=core.TYPES_TRAVAUX, width="medium"),
            "annee": st.column_config.NumberColumn(
                "Année", min_value=core.ANNEE_MIN, max_value=core.ANNEE_MAX, step=1, format="%d"),
            "commentaire": st.column_config.TextColumn("Commentaire", width="large"),
        },
    )

    b1, b2, b3 = st.columns(3)
    if b1.button("💾 Enregistrer", type="primary", use_container_width=True):
        if _enregistrer(edite, id_s, batiments):
            st.session_state["message"] = "Réponses enregistrées."
            st.rerun()

    if b2.button("Mettre « Non » sur les bâtiments non renseignés", use_container_width=True):
        edite = edite.copy()
        vides = edite["statut"].fillna("").eq("")
        edite.loc[vides, "statut"] = "Non"
        if _enregistrer(edite, id_s, batiments):
            st.session_state["message"] = f"« Non » appliqué à {int(vides.sum())} bâtiment(s) et enregistré."
            st.rerun()

    if b3.button("✅ Valider le questionnaire", use_container_width=True):
        manquants = int(edite["statut"].fillna("").eq("").sum())
        if manquants:
            st.error(f"{manquants} bâtiment(s) sans réponse. Complétez-les (ou utilisez "
                     "« Mettre Non sur les bâtiments non renseignés ») avant de valider.")
        elif _enregistrer(edite, id_s, batiments):
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
    synthese = core.avancement(db, structures, batiments)
    export = core.export_complet(db, structures, batiments)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Structures", len(synthese))
    c2.metric("Ayant commencé", int((synthese["nb_renseignes"] > 0).sum()))
    c3.metric("Validées", int(synthese["valide_le"].ne("").sum()))
    c4.metric("Bâtiments renseignés", f"{int(synthese['nb_renseignes'].sum())} / {len(batiments)}")

    st.subheader("Avancement par structure")
    st.dataframe(
        synthese, hide_index=True, use_container_width=True,
        column_config={"avancement_%": st.column_config.ProgressColumn(
            "Avancement", min_value=0, max_value=100, format="%d %%")},
    )

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
