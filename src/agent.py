# src/agent.py
import json
import time
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_REDACTION = "llama-3.3-70b-versatile"
MODEL_LEGER = "llama-3.1-8b-instant"

SCORE_REGENERATION_SEUIL = 6
MAX_RETRIES_API = 2


def _appel_groq(messages: list, model: str, temperature: float, max_tokens: int, json_mode: bool = True):
    """Centralise l'appel Groq avec retry simple sur erreurs transitoires (rate limit, timeout)."""
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    derniere_erreur = None
    for tentative in range(1, MAX_RETRIES_API + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            derniere_erreur = e
            print(f"⚠️ Erreur Groq (tentative {tentative}/{MAX_RETRIES_API}) : {e}")
            if tentative < MAX_RETRIES_API:
                time.sleep(2 * tentative)

    raise derniere_erreur


def _extraire_besoins(offre: dict) -> dict:
    """Étape 1 : Isoler ce que l'entreprise cherche vraiment."""
    prompt = f"""
    Analyse cette offre d'emploi et réponds UNIQUEMENT en JSON strict :
    {{
      "besoins_explicites": ["compétence/techno/outil demandé 1", "..."],
      "besoins_implicites": ["ce que l'entreprise cherche sans le dire explicitement"],
      "contexte_entreprise": "secteur, enjeu business ou mission déductible du texte",
      "mots_cles_a_reprendre": ["3 à 5 termes EXACTS du texte à réutiliser"]
    }}
    OFFRE : {offre.get('title')} chez {offre.get('company')}
    DESCRIPTION : {offre.get('description', '')[:3000]}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0.2,
            max_tokens=500,
        )
        resultat = json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur extraction besoins : {e}")
        resultat = {}

    return {
        "besoins_explicites": resultat.get("besoins_explicites") or [],
        "besoins_implicites": resultat.get("besoins_implicites") or [],
        "contexte_entreprise": resultat.get("contexte_entreprise") or "",
        "mots_cles_a_reprendre": resultat.get("mots_cles_a_reprendre") or [],
    }


def _evaluer_adequation(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str, besoins: dict) -> dict:
    """Étape 2A : Évaluer l'adéquation et extraire les points forts au format JSON."""
    prompt = f"""
    Tu es un Senior Data Manager & Recruteur Technique.
    Évalue l'adéquation du candidat avec l'offre d'emploi.

    BESOINS DE L'ENTREPRISE :
    - Explicites : {besoins.get('besoins_explicites')}
    - Implicites : {besoins.get('besoins_implicites')}

    DOSSIER CANDIDAT :
    [CV] : {cv_texte[:2000]}
    [PORTFOLIO] : {portfolio_texte[:1200]}
    [GITHUB] : {github_texte[:1500]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score_adequation": 85,
      "besoin_cle_entreprise": "Court résumé de la priorité absolue de l'entreprise",
      "preuve_technique_citee": "Nom précis du projet GitHub ou de la réalisation la plus pertinente",
      "points_forts": ["Point fort 1 aligné avec le besoin", "Point fort 2 avec preuve concrète"]
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0.2,
            max_tokens=600,
        )
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur évaluation adéquation : {e}")
        return {
            "score_adequation": 50,
            "besoin_cle_entreprise": "Analyse indisponible",
            "preuve_technique_citee": "",
            "points_forts": []
        }


def _rediger_lettre_texte(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str, besoins: dict, analyse: dict, retour_critique: str = None) -> str:
    """Étape 2B : Rédiger la lettre en texte brut (pas de JSON) pour garantir une longueur suffisante."""
    
    system_prompt = f"""
    Tu es un candidat expérimenté rédigant une LETTRE DE MOTIVATION SUR MESURE, PERCUTANTE ET STRUCTURÉE.
    
    CONSIGNES DE RÉDACTION STRICTES :
    - Longueur : 350 à 550 mots répartis en 4 PARAGRAPHES DISTINCTS avec des sauts de ligne purs entre eux.
    - Style : Professionnel, direct, "Je", axé sur les faits et preuves concrètes.
    
    STRUCTURE OBLIGATOIRE :
    1. PARAGRAPHE 1 (Accroche) : Lien direct avec le contexte et les enjeux de {offre.get('company')}.
    2. PARAGRAPHE 2 (Compétences clés) : Réponses aux besoins explicites : {besoins.get('besoins_explicites')}.
    3. PARAGRAPHE 3 (Preuves & Projets) : Développe en détail la réalisation '{analyse.get('preuve_technique_citee')}' issue du CV/GitHub avec résultats/chiffres.
    4. PARAGRAPHE 4 (Conclusion) : Proposition d'échange, disponibilité et formule de politesse.

    INTERDICTIONS STRICTES :
    - N'écris PAS dans un objet JSON. Rédige directement le texte de la lettre.
    - Pas de formules génériques ("candidat idéal", "passionné depuis toujours", "dynamique").
    - N'invente AUCUN projet absent des documents fournis.
    """

    if retour_critique:
        system_prompt += f"\n\n⚠️ ATTENTION : La version précédente manque de précision. Corrige spécifiquement ceci : {retour_critique}"

    user_prompt = f"""
    OFFRE : {offre.get('title')} chez {offre.get('company')}
    DESCRIPTION : {offre.get('description', '')[:3000]}

    DOSSIER CANDIDAT :
    [CV] : {cv_texte[:2000]}
    [PORTFOLIO] : {portfolio_texte[:1200]}
    [GITHUB] : {github_texte[:1500]}
    """

    r = _appel_groq(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=MODEL_REDACTION,
        temperature=0.4,
        max_tokens=2500,
        json_mode=False  # Relecture fluide en texte pur
    )
    return r.choices[0].message.content.strip()


def _critiquer_lettre(lettre: str, besoins: dict, preuve_citee: str, cv_texte: str, github_texte: str) -> dict:
    """Étape 3 : Évaluation qualité (spécificité et véracité)."""
    if not lettre:
        return {"score": 0, "justification": "Lettre vide."}

    prompt = f"""
    Évalue cette lettre de motivation sur deux critères :
    1) SPÉCIFICITÉ : Répond-elle à ces besoins ? {besoins.get('besoins_explicites', [])}
    2) VÉRACITÉ : La preuve "{preuve_citee}" existe-t-elle dans le CV/GitHub ?

    [EXTRAIT CV] : {cv_texte[:1000]}
    [EXTRAIT GITHUB] : {github_texte[:1000]}
    LETTRE : {lettre[:3000]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score": <entier de 0 à 10>,
      "justification": "1 phrase explicative"
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0,
            max_tokens=150,
        )
        res = json.loads(r.choices[0].message.content)
        return {"score": int(res.get("score", 10)), "justification": str(res.get("justification", ""))}
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        return {"score": 10, "justification": "Juge indisponible."}


def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """Pipeline principal de l'agent."""
    try:
        # 1. Extraction des besoins
        besoins = _extraire_besoins(offre)

        # 2. Évaluation de l'adéquation (JSON)
        analyse = _evaluer_adequation(offre, cv_texte, portfolio_texte, github_texte, besoins)

        # 3. Rédaction de la lettre (Texte brut complet)
        lettre = _rediger_lettre_texte(offre, cv_texte, portfolio_texte, github_texte, besoins, analyse)

        # 4. Auto-critique et regénération si nécessaire
        critique = _critiquer_lettre(lettre, besoins, analyse.get("preuve_technique_citee", ""), cv_texte, github_texte)

        if critique["score"] < SCORE_REGENERATION_SEUIL:
            print(f"  ⚠️ Lettre jugée insuffisante ({critique['score']}/10 : {critique['justification']}) — régénération...")
            lettre = _rediger_lettre_texte(
                offre, cv_texte, portfolio_texte, github_texte, besoins, analyse, retour_critique=critique["justification"]
            )

        nb_mots = len(lettre.split())
        print(f"✅ Lettre générée avec succès ({nb_mots} mots).")

        return {
            "score_adequation": int(analyse.get("score_adequation", 0)),
            "besoin_cle_entreprise": str(analyse.get("besoin_cle_entreprise", "")),
            "preuve_technique_citee": str(analyse.get("preuve_technique_citee", "")),
            "points_forts": analyse.get("points_forts", []),
            "lettre_motivation": lettre
        }

    except Exception as e:
        print(f"⚠️ Erreur globale agent : {e}")
        return None
