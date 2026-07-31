# src/agent.py
import json
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_REDACTION = "llama-3.3-70b-versatile"
MODEL_LEGER = "llama-3.1-8b-instant"


def _extraire_besoins(offre: dict) -> dict:
    """Étape 1 : isoler ce que l'entreprise cherche vraiment, avant toute rédaction."""
    prompt = f"""
    Analyse cette offre d'emploi et réponds UNIQUEMENT en JSON strict :
    {{
      "besoins_explicites": ["compétence/techno/outil demandé 1", "..."],
      "besoins_implicites": ["ce que l'entreprise cherche sans le dire explicitement (autonomie, gestion end-to-end, etc.)"],
      "contexte_entreprise": "secteur, enjeu business ou mission déductible du texte de l'offre",
      "mots_cles_a_reprendre": ["3 à 5 termes EXACTS du texte à réutiliser dans la lettre"]
    }}
    OFFRE : {offre.get('title')} chez {offre.get('company')}
    DESCRIPTION : {offre.get('description', '')[:3000]}
    """
    try:
        r = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_REDACTION,
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur extraction besoins : {e}")
        return {
            "besoins_explicites": [], "besoins_implicites": [],
            "contexte_entreprise": "", "mots_cles_a_reprendre": []
        }


def _critiquer_lettre(lettre: str, besoins: dict) -> int:
    """Étape 3 : score de 0 à 10 pour juger si la lettre est ancrée ou générique."""
    if not lettre:
        return 0
    prompt = f"""
    Note de 0 à 10 à quel point cette lettre répond PRÉCISÉMENT à ces besoins :
    {besoins.get('besoins_explicites', [])}
    (10 = ancrée dans des faits concrets du candidat + besoin réel de l'entreprise,
     0 = générique, interchangeable avec n'importe quelle autre entreprise).
    Réponds UNIQUEMENT avec le chiffre, rien d'autre.
    LETTRE : {lettre[:3000]}
    """
    try:
        r = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0,
            max_tokens=5
        )
        return int(r.choices[0].message.content.strip())
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        return 10  # en cas d'échec du scoring, on ne bloque pas le pipeline


def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    besoins = _extraire_besoins(offre)

    system_prompt = f"""
    Tu es un Senior Data Manager & Recruteur Technique ultra-exigeant.
    Évalue le dossier du candidat (CV, Portfolio, GitHub) par rapport à l'offre et rédige une
    LETTRE DE MOTIVATION COMPLÈTE ET STRUCTURÉE au nom du candidat ("Je").

    BESOINS DE L'ENTREPRISE DÉJÀ IDENTIFIÉS (à utiliser impérativement) :
    - Besoins explicites : {besoins.get('besoins_explicites')}
    - Besoins implicites : {besoins.get('besoins_implicites')}
    - Contexte entreprise : {besoins.get('contexte_entreprise')}
    - Mots-clés à réutiliser tels quels dans la lettre : {besoins.get('mots_cles_a_reprendre')}

    FORMAT DE SORTIE JSON STRICT ATTENDU :
    {{
      "score_adequation": 75,
      "besoin_cle_entreprise": "Court résumé du besoin",
      "preuve_technique_citee": "Nom du projet GitHub ou réalisation",
      "points_forts": ["Point 1", "Point 2"],
      "lettre_motivation": "Texte complet de la lettre..."
    }}

    CONSIGNES STRICTES POUR LA LETTRE ("lettre_motivation") :
    - COMPLÈTE (350 à 650 mots), pas une synthèse.
    - Structure obligatoire : 1) Accroche liée au contexte entreprise réel (pas générique)
      2) Compétences en lien direct avec les besoins explicites listés ci-dessus
      3) Preuve technique concrète : pour CHAQUE besoin explicite, cherche la correspondance
         la PLUS FORTE dans [CV]/[PORTFOLIO]/[GITHUB] et développe-la avec un résultat chiffré
         si possible. N'invente JAMAIS un projet absent des documents fournis — si aucune
         correspondance directe n'existe, explique en quoi une compétence proche est transférable.
      4) Conclusion & appel à l'action, disponibilité, formule de politesse professionnelle.
    - Rédigée au "Je", ton pro, direct, percutant.

    INTERDICTIONS STRICTES :
    - Pas de formules creuses ("passionné depuis toujours", "personne dynamique et motivée",
      "votre entreprise m'intéresse énormément", "candidat idéal").
    - Pas d'affirmation de compétence sans fait vérifiable à l'appui.
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
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=MODEL_REDACTION,
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        resultat = json.loads(response.choices[0].message.content)

        # Étape 3 : auto-critique + une seule tentative de regénération si trop générique
        score_qualite = _critiquer_lettre(resultat.get("lettre_motivation", ""), besoins)
        if score_qualite < 6:
            print(f"  ⚠️ Lettre jugée trop générique (score {score_qualite}/10) — regénération...")
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt + "\nATTENTION : la version précédente était jugée trop générique. Sois plus concret et plus spécifique à CETTE entreprise et CE besoin."},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL_REDACTION,
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            resultat = json.loads(response.choices[0].message.content)

        return resultat

    except Exception as e:
        print(f"⚠️ Erreur Groq API : {e}")
        return None
