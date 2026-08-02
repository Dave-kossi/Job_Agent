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
# FONCTIONS DE GESTION DES DONNÉES
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
# CHARGEMENT & FILTRES
# ==========================================
offres_brutes = charger_historique()

st.title("💼 Job Agent AI — Tableau de bord")
st.markdown("Explore et gère tes opportunités qualifiées par l'IA.")

# --- BARRE DE FILTRES ET TRI (Haut de page) ---
with st.container():
    col_search, col_source, col_sort = st.columns([2, 1, 1])

    # 1. Recherche par mot-clé
    search_query = col_search.text_input(
        "🔍 Rechercher (Entreprise, Titre, Compétence...)", 
        placeholder="Ex: Sephora, Python, NLP..."
    )

    # 2. Filtre par provenance / source
    sources_disponibles = ["Toutes"] + sorted(list(set([o.get("source", "Inconnue") for o in offres_brutes])))
    selected_source = col_source.selectbox("🌐 Provenance", sources_disponibles)

    # 3. Tri
    sort_option = col_sort.selectbox(
        "🔀 Trier par", 
        ["Plus récents d'abord", "Plus anciens d'abord", "Meilleur score IA"]
    )

# --- APPLICATION DES FILTRES ---
offres_filtrees = offres_brutes.copy()

# Filtre Recherche
if search_query:
    q = search_query.lower()
    offres_filtrees = [
        o for o in offres_filtrees 
        if q in o.get("title", "").lower() 
        or q in o.get("company", "").lower()
        or q in str(o.get("analyse", {})).lower()
    ]

# Filtre Source
if selected_source != "Toutes":
    offres_filtrees = [o for o in offres_filtrees if o.get("source", "Inconnue") == selected_source]

# Tri
if sort_option == "Plus récents d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=True)
elif sort_option == "Plus anciens d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=False)
elif sort_option == "Meilleur score IA":
    offres_filtrees.sort(key=lambda x: x.get("analyse", {}).get("score_adequation", 0), reverse=True)

st.divider()

# ==========================================
# ONGLETS DE NAVIGATION
# ==========================================
tab_offres, tab_sources, tab_gestion = st.tabs([
    f"🎯 Offres Qualifiées ({len(offres_filtrees)})", 
    "📊 Provenance & Stats", 
    "⚙️ Gestion & Nettoyage"
])

# ------------------------------------------
# ONGLET 1 : LES OFFRES FILTRÉES
# ------------------------------------------
with tab_offres:
    if not offres_filtrees:
        st.info("Aucune offre ne correspond à tes critères de recherche.")
    else:
        for item in offres_filtrees:
            analyse = item.get("analyse", {})
            score = analyse.get("score_adequation", 0)
            source = item.get("source", "Source inconnue")
            date_raw = item.get("date_ajout", "")

            # Calcul du temps écoulé (ex: "Il y a 2h" ou date précise)
            if date_raw:
                try:
                    dt = datetime.fromisoformat(date_raw)
                    date_affichee = dt.strftime("%d/%m/%Y à %H:%M")
                except ValueError:
                    date_affichee = "Date inconnue"
            else:
                date_affichee = "Date inconnue"

            badge_score = "🟢" if score >= 85 else "🟠"

            with st.expander(f"{badge_score} **{item.get('title')}** — {item.get('company')} | {score}% Match ({source})"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"📅 Ajoutée le : **{date_affichee}**")
                c2.caption(f"🌐 Provenance : **{source}**")
                c3.markdown(f"🔗 [Consulter l'offre]({item.get('url')})")

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

# ------------------------------------------
# ONGLET 2 : STATISTIQUES & PROVENANCE
# ------------------------------------------
with tab_sources:
    st.header("📊 Répartition par Provenance")
    if offres_brutes:
        # Compteur par source
        counts = {}
        for o in offres_brutes:
            s = o.get("source", "Autre")
            counts[s] = counts.get(s, 0) + 1
        
        cols = st.columns(len(counts))
        for idx, (src_name, count) in enumerate(counts.items()):
            cols[idx].metric(f"Offres {src_name}", count)
    else:
        st.write("Pas de données disponibles.")

# ------------------------------------------
# ONGLET 3 : CENTRE DE PURGE
# ------------------------------------------
with tab_gestion:
    st.header("⚙️ Nettoyage de l'historique")
    st.write("Les offres datant de plus de **2 jours** sont purgées automatiquement à chaque passage.")
    
    if st.button("🧹 Purger les offres obsolètes maintenant", type="primary"):
        limite = datetime.now() - timedelta(days=2)
        recentes = [o for o in offres_brutes if datetime.fromisoformat(o.get("date_ajout", datetime.now().isoformat())) >= limite]
        sauvegarder_historique(recentes)
        st.success("Nettoyage manuel effectué !")
        st.rerun()
