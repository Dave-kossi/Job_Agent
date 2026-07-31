import os
import json
import pandas as pd

from src.parser import lire_cv_pdf, lire_portfolio_html
from src.github_parser import lire_profil_github
from src.scraper import collecter_offres
from src.company_scraper import collecter_offres_grands_groupes
from src.agent import analyser_et_rediger

CHEMIN_HISTORIQUE = "data/historique.json"

# ==========================================
# 1. GESTION DE L'HISTORIQUE (JSON)
# ==========================================
def charger_historique() -> list:
    """Charge la liste des offres déjà traitées."""
    if os.path.exists(CHEMIN_HISTORIQUE):
        try:
            with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erreur de lecture de l'historique : {e}")
            return []
    return []

def sauvegarder_historique(historique: list):
    """Sauvegarde les offres qualifiées dans le fichier JSON."""
    os.makedirs(os.path.dirname(CHEMIN_HISTORIQUE), exist_ok=True)
    with open(CHEMIN_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. COLLECTE MULTI-SOURCES
# ==========================================
def tout_rassembler() -> pd.DataFrame:
    """Rassemble et fusionne les offres de toutes les sources."""
    print("\n🔄 Collecte globale en cours...")
    
    # A. Agrégateurs (LinkedIn, Indeed, Google, WTTJ)
    df_general = collecter_offres(limites=5)
    
    # B. API directes des Grands Groupes (Thales, Airbus, EDF, SG, BNP)
    offres_entreprises = collecter_offres_grands_groupes(mot_cle="Data Stage", limite=5)
    df_entreprises = pd.DataFrame(offres_entreprises)
    
    # C. Fusion & Dédoublonnage
    liste_df = [df for df in [df_general, df_entreprises] if not df.empty]
    
    if liste_df:
        df_final = pd.concat(liste_df, ignore_index=True)
        # Élimination des lignes sans URL ou doublons sur l'URL
        df_final = df_final.dropna(subset=['job_url'])
        df_final = df_final.drop_duplicates(subset=['job_url'], keep='first')
        return df_final
    
    return pd.DataFrame()

# ==========================================
# 3. WORKFLOW PRINCIPAL DE L'AGENT
# ==========================================
def execution_job():
    print("\n🚀 [AGENT] Démarrage du check d'offres...")
    
    # Lecture des données candidat
    cv_texte = lire_cv_pdf("data/cv.pdf")
    portfolio_texte = lire_portfolio_html("data/portfolio.html")
    github_texte = lire_profil_github("Dave-kossi")
    
    historique = charger_historique()
    ids_connus = [item['id'] for item in historique]

    # Collecte des opportunités
    offres = tout_rassembler()
    
    if offres.empty:
        print("❌ Aucune offre trouvée lors de ce passage.")
        print("🏁 [AGENT] Fin de l'exécution.")
        return

    print(f"📊 {len(offres)} offres uniques à analyser au total.\n")
    
    # Analyse LLM par offre
    for _, row in offres.iterrows():
        job_id = str(row.get('job_url', ''))
        
        # Filtre anti-doublons
        if not job_id or job_id in ids_connus:
            continue
            
        entreprise = row.get('company', 'Inconnue')
        titre = row.get('title', 'Sans titre')
        
        print(f"⚡ Analyse par le LLM : '{titre}' chez {entreprise}...")
        
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
                "analyse": analyse
            }
            historique.append(resultat)
            print(f"  └─ ✅ Offre qualifiée ! (Match : {analyse['score_adequation']}%)")
        else:
            score = analyse.get('score_adequation', 0) if analyse else 0
            print(f"  └─ ❌ Offre écartée (Match : {score}%)")
        
        # On enregistre l'ID comme traité
        ids_connus.append(job_id)

    sauvegarder_historique(historique)
    print("\n✅ [AGENT] Enregistrement terminé avec succès !")

# ==========================================
# 4. EXÉCUTION DE L'AGENT
# ==========================================
if __name__ == "__main__":
    print("🤖 Agent Autonome démarré !")
    execution_job()
