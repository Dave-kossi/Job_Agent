# src/agent.py
import json
import os
from groq import Groq

# Initialisation du client (lit automatiquement la variable d'environnement GROQ_API_KEY)
client = Groq(api_key=os.getenv("GROQ_API_KEY", "TON_API_KEY_ICI"))

def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    prompt = f"""
[RÔLE]
Tu es un Senior Data Manager & Recruteur Technique ultra-exigeant. 
Évalue le dossier du candidat (CV, Portfolio, GitHub) par rapport à l'offre et rédige la lettre de motivation parfaite AU NOM DU CANDIDAT ("Je").

=========================================
OFFRE : {offre.get('title')} chez {offre.get('company')}
DESCRIPTION : {offre.get('description', '')[:2000]}
=========================================
DOSSIER CANDIDAT :
[CV] : {cv_texte[:1200]}
[PORTFOLIO] : {portfolio_texte[:800]}
[GITHUB] : {github_texte[:1000]}
=========================================

CONSIGNES :
1. Analyse le besoin technique principal de l'entreprise.
2. Identifie dans le GitHub ou le CV du candidat le projet exact qui sert de preuve technique.
3. Rédige une lettre très courte (150 mots max) au "Je", percutante et directe. Ne commence JAMAIS par "Actuellement étudiant...".

FORMAT DE SORTIE JSON STRICT ATTENDU :
{{
  "score_adequation": 85,
  "besoin_cle_entreprise": "Court résumé du besoin",
  "preuve_technique_citee": "Nom du projet GitHub ou réalisation",
  "points_forts": ["Point 1", "Point 2"],
  "lettre_motivation": "Texte de la lettre rédigée au 'Je'..."
}}
"""

    try:
        # Modèle recommandé : llama-3.1-8b-instant (ultra-rapide et très précis)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        contenu = response.choices[0].message.content
        return json.loads(contenu)

    except Exception as e:
        print(f"⚠️ Erreur Groq API : {e}")
        return None