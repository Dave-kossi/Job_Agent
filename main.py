import os
import json
import pandas as pd
from datetime import datetime, timedelta

from src.parser import lire_cv_pdf, lire_portfolio_html
from src.github_parser import lire_profil_github
from src.scraper import collecter_offres
from src.company_scraper import collecter_offres_grands_groupes
from src.agent import analyser_et_rediger

CHEMIN_HISTORIQUE = "data/historique.json"
JOURS_RETENTION_MAX = 2  # Conserve uniquement les offres des 2 derniers jours

# ==========================================
# FILTRES STRICTS : DATA SCIENCE / ML / IA
# ==========================================
MOTS_CLES_DOMAINE = [
    "data science", "data scientist", "machine learning", "ml", 
    "deep learning", "intelligence artificielle", "ia", "ai",
    "nlp", "computer vision", "llm", "generative ai", "data engineer"
]

MOTS_CLES_CONTRAT = ["stage", "intern", "internship"]


def est_stage_data_valide(titre: str, description: str) -> bool:
    """
    Vérifie rigoureusement que l'offre concerne un STAGE 
    dans le domaine de la Data Science, du ML ou de l'IA.
    """
    texte = f"{titre} {description}".lower()
    
    # 1. Doit obligatoirement mentionner un contrat de type Stage/Internship
    est_stage = any(mot in texte for mot in MOTS_CLES_CONTRAT)
    
    # 2. Doit concerner les thématiques ciblées (Data Science / ML / IA)
    est_data_ml_ia = any(mot in texte for mot in MOTS_CLES_DOMAINE)
    
    return est_stage and est_data_ml_ia


# ==========================================
# 1. GESTION ET PURGE DE L'HISTORIQUE (JSON)
# ==========================================
def charger_et_nettoyer_historique(jours_max: int = JOURS_RETENTION_MAX) -> list:
    """Charge l'historique et purge automatiquement les offres de plus de X jours."""
    if not os.path.exists(CHEMIN_HISTORIQUE):
        return []

    try:
        with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
            historique = json.load(f)

        limite_date = datetime.now() - timedelta(days=jours_max)
        historique_filtre = []
        offres_purgees = 0

        for item in historique:
            date_ajout_str = item.get("date_ajout")
            if date_ajout_str:
                try:
                    date_ajout = datetime.fromisoformat(date_ajout_str)
                except ValueError:
                    date_ajout = datetime.now()
            else:
                date_ajout = datetime.now()

            # Conservation des offres récentes uniquement (<= 2 jours)
            if date_ajout >= limite_date:
                historique_filtre.append(item)
            else:
                offres_purgees += 1

        if offres_purgees > 0:
            print(f"🧹 Purge automatique : {offres_purgees} offre(s) de plus de {jours_max} jours supprimée(s).")

        return historique_filtre

    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de l'historique : {e}")
        return []


def sauvegarder_historique(historique: list):
    """Sauvegarde la liste des offres dans le fichier JSON."""
    os.makedirs(os.path.dirname(CHEMIN_HISTORIQUE), exist_ok=True)
    with open(CHEMIN_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


# ==========================================
# 2. COLLECTE MULTI-SOURCES & PRÉ-FILTRAGE
# ==========================================
def tout_rassembler() -> pd.DataFrame:
    """
    Rassemble les offres de toutes les sources (JobSpy, WTTJ, Stage.fr, Grands Groupes dont Eiffage)
    et filtre exclusivement les stages Data Science / ML / IA.
    """
    print("\n🔄 Collecte globale des opportunités (Data Science, ML & IA)...")
    
    # A. Agrégateurs (JobSpy + Welcome to the Jungle + Stage.fr)
    df_general = collecter_offres(limites=5)
    
    # B. Grands Groupes (Airbus, Thales, SG, BNP Paribas, Eiffage)
    offres_entreprises = collecter_offres_grands_groupes(mot_cle="Stage Data Science", limite=5)
    df_entreprises = pd.DataFrame(offres_entreprises)
    
    # C. Fusion & Dédoublonnage
    liste_df = [df for df in [df_general, df_entreprises] if isinstance(df, pd.DataFrame) and not df.empty]
    
    if not liste_df:
        return pd.DataFrame()

    df_brut = pd.concat(liste_df, ignore_index=True)
    df_brut = df_brut.dropna(subset=['job_url'])
    df_brut = df_brut.drop_duplicates(subset=['job_url'], keep='first')

    # D. Filtre strict de pré-qualification Data Science / ML / IA
    offres_filtrees = []
    for _, row in df_brut.iterrows():
        titre = str(row.get('title', ''))
        desc = str(row.get('description', ''))
        
        if est_stage_data_valide(titre, desc):
            offres_filtrees.append(row)
            
    print(f"🔍 {len(df_brut)} offres scannées au total ➔ {len(offres_filtrees)} stages Data/ML/IA validés.")
    return pd.DataFrame(offres_filtrees)


# ==========================================
# 3. WORKFLOW PRINCIPAL DE L'AGENT
# ==========================================
def execution_job():
    print("\n🚀 [AGENT DATA SCIENCE / ML / IA] Démarrage du scan d'offres...")
    
    # Lecture du profil candidat
    cv_texte = lire_cv_pdf("data/cv.pdf")
    portfolio_texte = lire_portfolio_html("data/portfolio.html")
    github_texte = lire_profil_github("Dave-kossi")
    
    # Charge et purge l'historique (< 2 jours)
    historique = charger_et_nettoyer_historique(JOURS_RETENTION_MAX)
    ids_connus = [item['id'] for item in historique]

    # Collecte des opportunités ciblées
    offres = tout_rassembler()
    
    if offres.empty:
        print("❌ Aucune nouvelle offre de stage Data/ML/IA trouvée lors de ce passage.")
        sauvegarder_historique(historique)
        print("🏁 [AGENT] Fin de l'exécution.")
        return

    print(f"📊 {len(offres)} stages en Data/ML/IA à évaluer par l'IA...\n")
    
    # Analyse LLM par offre
    for _, row in offres.iterrows():
        job_id = str(row.get('job_url', ''))
        
        # Filtre anti-doublons (déjà traitées ou déjà en base)
        if not job_id or job_id in ids_connus:
            continue
            
        entreprise = row.get('company', 'Inconnue')
        titre = row.get('title', 'Sans titre')
        
        # Provenance exacte (Eiffage, Stage.fr, WTTJ, LinkedIn, etc.)
        raw_site = row.get('site', 'Autre')
        source_plateforme = str(raw_site).capitalize() if raw_site else "Autre"
        
        print(f"⚡ Analyse IA : '{titre}' chez {entreprise} (Source: {source_plateforme})...")
        
        offre_dict = {
            'company': entreprise,
            'title': titre,
            'description': str(row.get('description', ''))
        }
        
        analyse = analyser_et_rediger(offre_dict, cv_texte, portfolio_texte, github_texte)
        
        if analyse and analyse.get('score_adequation', 0) >= 70:
            resultat = {
                "id": job_id,
                "title": titre,
                "company": entreprise,
                "url": job_id,
                "source": source_plateforme,        # Enregistré pour les filtres Streamlit
                "date_ajout": datetime.now().isoformat(),  # Date ISO pour la purge 2 jours
                "analyse": analyse
            }
            historique.append(resultat)
            print(f"  └─ ✅ Stage retenu ! (Match : {analyse['score_adequation']}%)")
        else:
            score = analyse.get('score_adequation', 0) if analyse else 0
            print(f"  └─ ❌ Stage écarté (Match : {score}%)")
        
        # Marquage pour éviter les répétitions dans le même run
        ids_connus.append(job_id)

    # Sauvegarde finale du fichier JSON
    sauvegarder_historique(historique)
    print("\n✅ [AGENT] Traitement et sauvegarde réussis !")


# ==========================================
# 4. EXÉCUTION EN POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    print("🤖 Agent Autonome (Focus Stages Data Science / ML / IA) démarré !")
    execution_job()
