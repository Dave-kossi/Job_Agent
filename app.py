import os
import json
import streamlit as st
from datetime import datetime, timedelta

CHEMIN_HISTORIQUE = "data/historique.json"

st.set_page_config(
    page_title="Job Agent AI",
    page_icon="💼",
    layout="wide"
)

# ==========================================
# FONCTIONS DE GESTION DU STOCKAGE
# ==========================================
def charger_historique() -> list:
    if os.path.exists(CHEMIN_HISTORIQUE):
        try:
            with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def sauvegarder_historique(data: list):
    os.makedirs(os.path.dirname(CHEMIN_HISTORIQUE), exist_ok=True)
    with open(CHEMIN_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# INTERFACE PRINCIPALE STREAMLIT
# ==========================================
st.title("💼 Job Agent AI — Tableau de bord")
st.markdown("Suivi en temps réel des offres d'emploi qualifiées par l'Agent IA.")

# Onglets principaux
tab_offres, tab_gestion = st.tabs(["🎯 Offres Qualifiées", "⚙️ Gestion & Nettoyage"])

# ------------------------------------------
# ONGLET 1 : LES OFFRES
# ------------------------------------------
with tab_offres:
    offres = charger_historique()

    if not offres:
        st.info("Aucune offre retenue pour le moment. L'agent effectuera sa prochaine analyse sous peu.")
    else:
        st.subheader(f"📋 {len(offres)} opportunité(s) active(s)")
        
        for item in offres:
            analyse = item.get("analyse", {})
            score = analyse.get("score_adequation", 0)
            date_ajout_raw = item.get("date_ajout", "")
            
            # Formatage de la date d'affichage
            if date_ajout_raw:
                try:
                    date_affichee = datetime.fromisoformat(date_ajout_raw).strftime("%d/%m/%Y à %H:%H")
                except ValueError:
                    date_affichee = "Inconnue"
            else:
                date_affichee = "Inconnue"

            # Badge de couleur selon le score
            couleur_score = "🟢" if score >= 80 else "🟠"

            with st.expander(f"{couleur_score} **{item.get('title')}** — {item.get('company')} (Score : {score}%)"):
                col_meta1, col_meta2 = st.columns(2)
                col_meta1.caption(f"🗓️ Ajoutée le : **{date_affichee}**")
                col_meta2.markdown(f"🔗 [Consulter l'annonce officielle]({item.get('url')})")

                st.markdown("---")

                # Points forts et besoin entreprise
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown("**🎯 Besoin clé de l'entreprise :**")
                    st.write(analyse.get("besoin_cle_entreprise", "Non spécifié"))
                    st.markdown("**📌 Preuve technique sélectionnée :**")
                    st.write(analyse.get("preuve_technique_citee", "Non spécifiée"))

                with col_info2:
                    st.markdown("**💪 Points forts identifiés :**")
                    points = analyse.get("points_forts", [])
                    if isinstance(points, list):
                        for pt in points:
                            st.write(f"- {pt}")
                    else:
                        st.write(points)

                st.markdown("---")
                st.markdown("### ✉️ Lettre de motivation générée")
                st.info(analyse.get("lettre_motivation", "Aucune lettre générée."))

# ------------------------------------------
# ONGLET 2 : CENTRE DE PURGE & DE GESTION
# ------------------------------------------
with tab_gestion:
    st.header("⚙️ Gestion de l'historique")
    st.write("L'agent purge automatiquement les annonces datant de **plus de 4 jours**. Vous pouvez également effectuer une maintenance manuelle ci-dessous.")

    offres = charger_historique()
    limite_4_jours = datetime.now() - timedelta(days=4)

    offres_recentes = []
    offres_obsoletes = []

    for item in offres:
        date_str = item.get("date_ajout")
        if date_str:
            try:
                date_dt = datetime.fromisoformat(date_str)
                if date_dt < limite_4_jours:
                    offres_obsoletes.append(item)
                else:
                    offres_recentes.append(item)
            except ValueError:
                offres_recentes.append(item)
        else:
            offres_recentes.append(item)

    # Indicateurs de performance
    m1, m2, m3 = st.columns(3)
    m1.metric("Total offres en mémoire", len(offres))
    m2.metric("Offres récentes (≤ 4 jours)", len(offres_recentes))
    m3.metric("Offres périmées (> 4 jours)", len(offres_obsoletes))

    st.markdown("---")

    # Boutons d'action
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.subheader("🧹 Nettoyage ciblé")
        if st.button("Purger les offres de +4 jours", type="primary", use_container_width=True):
            sauvegarder_historique(offres_recentes)
            st.success(f"Nettoyage effectué : {len(offres_obsoletes)} offre(s) supprimée(s).")
            st.rerun()

    with col_act2:
        st.subheader("⚠️ Réinitialisation complète")
        with st.popover("Effacer TOUTES les offres"):
            st.warning("Cette action supprimera la totalité de vos offres enregistrées.")
            if st.button("Confirmer la suppression totale", use_container_width=True):
                sauvegarder_historique([])
                st.success("L'historique a été entièrement effacé.")
                st.rerun()
