# src/agent.py
import json
import os
from groq import Groq

# Initialisation du client (lit automatiquement la variable d'environnement GROQ_API_KEY)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    
    system_prompt = """
    Tu es un Senior Data Manager & Recruteur Technique ultra-exigeant.
    Évalue le dossier du candidat (CV, Portfolio, GitHub) par rapport à l'offre et rédige une LETTRE DE MOTIVATION COMPLÈTE ET STRUCTURÉE au nom du candidat ("Je").

    FORMAT DE SORTIE JSON STRICT ATTENDU :
    {
      "score_adequation": 75,
      "besoin_cle_entreprise": "Court résumé du besoin",
      "preuve_technique_citee": "Nom du projet GitHub ou réalisation",
      "points_forts": ["Point 1", "Point 2"],
      "lettre_motivation": "Texte complet de la lettre..."
    }

    CONSIGNES STRICTES POUR LA LETTRE DE MOTIVATION ("lettre_motivation") :
    - La lettre doit être COMPLÈTE (entre 350 et 650 mots), pas une simple synthèse ou un paragraphe de conclusion.
    - Structure OBLIGATOIRE :
      1. Accroche / Entreprise : Pourquoi cette entreprise et ce poste vous intéressent.
      2. Profil / Compétences : Vos points forts en Data Science / ML en lien direct avec l'offre.
      3. Preuve technique : Un exemple concret tiré du CV, Portfolio ou GitHub (ex: projet de transition énergétique, modèles ML, etc.).
      4. Conclusion & Appel à l'action : Disponibilité pour un entretien et formule de politesse professionnelle.
    - Rédigée au "Je", ton pro, direct et percutant.
    """

    user_prompt = f"""
    =========================================
    OFFRE : {offre.get('title')} chez {offre.get('company')}
    DESCRIPTION : {offre.get('description', '')[:3000]}
    =========================================
    DOSSIER CANDIDAT :
    [CV] : {cv_texte[:2000]}
    [PORTFOLIO] : {portfolio_texte[:1200]}
    [GITHUB] : {github_texte[:1500]}
    =========================================
    """

    try:
        # Utilisation de llama-3.3-70b-versatile pour une qualité de rédaction nettement supérieure
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        contenu = response.choices[0].message.content
        return json.loads(contenu)

    except Exception as e:
        print(f"⚠️ Erreur Groq API : {e}")
        return None
