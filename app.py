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
# FONCTIONS DE GESTION DU FICHIER JSON
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
# CHARGEMENT & BARRE DE FILTRES
# ==========================================
offres_brutes = charger_historique()

st.title("💼 Job Agent AI — Tableau de bord")
st.markdown("Explore et gère tes opportunités qualifiées par l'IA.")

# --- CONTROLES DE RECHERCHE ET TRI ---
with st.container():
    col_search, col_source, col_sort = st.columns([2, 1, 1])

    # 1. Recherche globale
    search_query = col_search.text_input(
        "🔍 Rechercher (Entreprise, Titre, Compétence...)", 
        placeholder="Ex: Sephora, Python, NLP..."
    )

    # 2. Filtre Provenance
    sources = ["Toutes"] + sorted(list(set([o.get("source", "Inconnue") for o in offres_brutes])))
    selected_source = col_source.selectbox("🌐 Provenance", sources)

    # 3. Tri Chronologique / Pertinence
    sort_option = col_sort.selectbox(
        "🔀 Trier par", 
        ["Plus récents d'abord", "Plus anciens d'abord", "Meilleur score IA"]
    )

# --- APPLICATION DES FILTRES ---
offres_filtrees = offres_brutes.copy()

if search_query:
    q = search_query.lower()
    offres_filtrees = [
        o for o in offres_filtrees 
        if q in o.get("title", "").lower() 
        or q in o.get("company", "").lower()
        or q in str(o.get("analyse", {})).lower()
    ]

if selected_source != "Toutes":
    offres_filtrees = [o for o in offres_filtrees if o.get("source", "Inconnue") == selected_source]

if sort_option == "Plus récents d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=True)
elif sort_option == "Plus anciens d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=False)
elif sort_option == "Meilleur score IA":
    offres_filtrees.sort(key=lambda x: x.get("analyse", {}).get("score_adequation", 0), reverse=True)

st.divider()

# ==========================================
# ONGLETS DE L'APPLICATION
# ==========================================
tab_offres, tab_sources, tab_gestion = st.tabs([
    f"🎯 Offres Qualifiées ({len(offres_filtrees)})", 
    "📊 Provenance & Stats", 
    "⚙️ Gestion & Purge"
])

# ------------------------------------------
# ONGLET 1 : LES OFFRES
# ------------------------------------------
with tab_offres:
    if not offres_filtrees:
        st.info("Aucune offre ne correspond à tes critères actuels.")
    else:
        for idx, item in enumerate(offres_filtrees):
            analyse = item.get("analyse", {})
            score = analyse.get("score_adequation", 0)
            source = item.get("source", "Source inconnue")
            date_raw = item.get("date_ajout", "")

            if date_raw:
                try:
                    dt = datetime.fromisoformat(date_raw)
                    date_affichee = dt.strftime("%d/%m/%Y à %H:%M")
                except ValueError:
                    date_affichee = "Date inconnue"
            else:
                date_affichee = "Date inconnue"

            badge_score = "🟢" if score >= 80 else "🟠"

            with st.expander(f"{badge_score} **{item.get('title')}** — {item.get('company')} | {score}% Match ({source})"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"📅 Ajoutée le : **{date_affichee}**")
                c2.caption(f"🌐 Source : **{source}**")
                c3.markdown(f"🔗 [Ouvrir l'offre sur le site]({item.get('url')})")

                st.markdown("---")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**🎯 Besoin clé :**")
                    st.write(analyse.get("besoin_cle_entreprise", "Non précisé"))
                    st.markdown("**📌 Preuve technique :**")
                    st.write(analyse.get("preuve_technique_citee", "Non précisée"))

                with col_b2:
                    st.markdown("**💪 Points forts :**")
                    pts = analyse.get("points_forts", [])
                    if isinstance(pts, list):
                        for p in pts:
                            st.write(f"- {p}")
                    else:
                        st.write(pts)

                st.markdown("---")
                st.markdown("### ✉️ Lettre de motivation générée")
                st.info(analyse.get("lettre_motivation", "Lettre non disponible."))
                
                # Bouton pour supprimer une offre spécifique de la base
                if st.button(f"🗑️ Supprimer cette offre", key=f"del_{item.get('id', idx)}"):
                    nouvelles_offres = [o for o in offres_brutes if o.get('id') != item.get('id')]
                    sauvegarder_historique(nouvelles_offres)
                    st.success("Offre retirée de la base de données.")
                    st.rerun()

# ------------------------------------------
# ONGLET 2 : STATISTIQUES DE PROVENANCE
# ------------------------------------------
with tab_sources:
    st.header("📊 Statistiques par plateforme")
    if offres_brutes:
        counts = {}
        for o in offres_brutes:
            s = o.get("source", "Autre")
            counts[s] = counts.get(s, 0) + 1
        
        cols = st.columns(max(len(counts), 1))
        for idx, (src_name, count) in enumerate(counts.items()):
            cols[idx].metric(f"Offres {src_name}", count)
    else:
        st.write("Aucune offre disponible en mémoire.")

# ------------------------------------------
# ONGLET 3 : CENTRE DE PURGE (2 JOURS)
# ------------------------------------------
with tab_gestion:
    st.header("⚙️ Centre de maintenance & Purge mémoire")
    st.write("Utilise ces options pour libérer la mémoire JSON et ne garder que les données récentes.")

    limite_2_jours = datetime.now() - timedelta(days=2)
    
    # Séparation des offres récentes et obsolètes
    offres_recentes = []
    offres_obsoletes = []

    for item in offres_brutes:
        date_str = item.get("date_ajout")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str)
                if dt < limite_2_jours:
                    offres_obsoletes.append(item)
                else:
                    offres_recentes.append(item)
            except ValueError:
                offres_recentes.append(item)
        else:
            offres_recentes.append(item)

    # Affichage des métriques de la base
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Stock total en base", len(offres_brutes))
    col_m2.metric("Moins de 2 jours", len(offres_recentes))
    col_m3.metric("Obsolètes (+2 jours)", len(offres_obsoletes))

    st.markdown("---")

    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.subheader("🧹 Purge programmée (2 jours)")
        st.caption("Supprime immédiatement les offres datant de plus de 48 heures.")
        if st.button("Purger les offres de +2 jours", type="primary", use_container_width=True):
            sauvegarder_historique(offres_recentes)
            st.success(f"Purge réussie : {len(offres_obsoletes)} offre(s) supprimée(s) !")
            st.rerun()

    with col_act2:
        st.subheader("⚠️ Réinitialisation complète")
        st.caption("Vide totalement la base de données JSON.")
        with st.popover("Vider l'historique complet"):
            st.warning("Attention : cette action effacera absolument toutes les offres en mémoire.")
            if st.button("Confirmer l'effacement total", use_container_width=True):
                sauvegarder_historique([])
                st.success("La base de données a été réinitialisée.")
                st.rerun()
