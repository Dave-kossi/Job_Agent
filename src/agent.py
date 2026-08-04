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


def _appel_groq(messages: list, model: str, temperature: float, max_tokens: int,
                 json_mode: bool = True):
    """Centralise l'appel Groq avec retry simple sur erreurs transitoires
    (rate limit, timeout réseau) — évite de perdre une offre à cause
    d'un 429 ponctuel."""
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
                time.sleep(2 * tentative)  # backoff simple : 2s puis 4s

    raise derniere_erreur


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
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_REDACTION,
            temperature=0.2,
            max_tokens=500,
        )
        resultat = json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur extraction besoins : {e}")
        resultat = {}

    # Validation défensive — évite de propager des clés manquantes/mal typées
    # dans le reste du pipeline (agent.py comme le juge en dépendent).
    return {
        "besoins_explicites": resultat.get("besoins_explicites") or [],
        "besoins_implicites": resultat.get("besoins_implicites") or [],
        "contexte_entreprise": resultat.get("contexte_entreprise") or "",
        "mots_cles_a_reprendre": resultat.get("mots_cles_a_reprendre") or [],
    }


def _critiquer_lettre(lettre: str, besoins: dict, preuve_citee: str,
                       cv_texte: str, github_texte: str) -> dict:
    """Étape 3 : juge la lettre sur DEUX axes —
    1) spécificité (ancrée dans le besoin réel de l'entreprise, pas générique)
    2) véracité (la preuve technique citée existe bien dans le CV/GitHub fourni)
    Retourne un score 0-10 + une justification courte, utilisée ensuite
    pour guider une éventuelle regénération de façon ciblée."""
    if not lettre:
        return {"score": 0, "justification": "Lettre vide."}

    prompt = f"""
    Tu es un relecteur exigeant. Évalue cette lettre de motivation sur deux critères :

    1) SPÉCIFICITÉ : répond-elle précisément à ces besoins de l'entreprise ?
       {besoins.get('besoins_explicites', [])}
       (générique = interchangeable avec n'importe quelle autre entreprise)

    2) VÉRACITÉ : la preuve technique citée ("{preuve_citee}") est-elle bien
       vérifiable dans les documents du candidat ci-dessous ? Si la lettre
       affirme un résultat ou un projet qui n'apparaît PAS dans ces extraits,
       signale-le explicitement dans ta justification.

    [EXTRAIT CV] : {cv_texte[:1000]}
    [EXTRAIT GITHUB] : {github_texte[:1000]}

    LETTRE À ÉVALUER : {lettre[:3000]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score": <entier de 0 à 10>,
      "justification": "1 phrase courte : pourquoi ce score, et quel besoin explicite n'est pas couvert ou quelle preuve semble non vérifiable, le cas échéant"
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0,
            max_tokens=120,
        )
        resultat = json.loads(r.choices[0].message.content)
        score = int(resultat.get("score", 10))
        justification = str(resultat.get("justification", ""))
        return {"score": score, "justification": justification}
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        # En cas d'échec du juge, on ne bloque pas le pipeline —
        # score neutre haut pour ne pas forcer une regénération inutile.
        return {"score": 10, "justification": "Juge indisponible — score par défaut."}


def _valider_resultat(resultat: dict) -> dict:
    """Garantit que toutes les clés attendues en aval (main.py, app.py)
    sont présentes avec le bon type, même si le LLM a omis un champ."""
    if not isinstance(resultat, dict):
        resultat = {}

    score = resultat.get("score_adequation", 0)
    try:
        score = int(score)
    except (ValueError, TypeError):
        score = 0

    points_forts = resultat.get("points_forts", [])
    if not isinstance(points_forts, list):
        points_forts = [str(points_forts)] if points_forts else []

    return {
        "score_adequation": score,
        "besoin_cle_entreprise": str(resultat.get("besoin_cle_entreprise", "") or ""),
        "preuve_technique_citee": str(resultat.get("preuve_technique_citee", "") or ""),
        "points_forts": points_forts,
        "lettre_motivation": str(resultat.get("lettre_motivation", "") or ""),
    }


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
    - COMPLÈTE (350 à 650 mots), structurée en 4 paragraphes distincts.
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
        response = _appel_groq(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=MODEL_REDACTION,
            temperature=0.3,
            max_tokens=1500,
        )
        resultat = _valider_resultat(json.loads(response.choices[0].message.content))

        # Étape 3 : auto-critique (spécificité + véracité) + une seule
        # regénération, guidée par la justification du juge.
        critique = _critiquer_lettre(
            resultat.get("lettre_motivation", ""),
            besoins,
            resultat.get("preuve_technique_citee", ""),
            cv_texte,
            github_texte,
        )

        if critique["score"] < SCORE_REGENERATION_SEUIL:
            print(f"  ⚠️ Lettre jugée insuffisante (score {critique['score']}/10 — {critique['justification']}) — regénération...")

            system_prompt_v2 = system_prompt + f"""

            ATTENTION : la version précédente a été jugée insuffisante par un relecteur.
            Motif précis à corriger : {critique['justification']}
            Corrige spécifiquement ce point — ne te contente pas de reformuler,
            comble le manque identifié ou remplace la preuve non vérifiable par
            une correspondance réelle trouvée dans [CV]/[PORTFOLIO]/[GITHUB].
            """

            response = _appel_groq(
                messages=[
                    {"role": "system", "content": system_prompt_v2},
                    {"role": "user", "content": user_prompt},
                ],
                model=MODEL_REDACTION,
                temperature=0.5,
                max_tokens=1500,
            )
            resultat = _valider_resultat(json.loads(response.choices[0].message.content))

        # Vérification post-hoc de la longueur — les LLM comptent mal les mots,
        # on log un écart plutôt que de faire une confiance aveugle à la consigne.
        nb_mots = len(resultat["lettre_motivation"].split())
        if nb_mots and not (300 <= nb_mots <= 700):
            print(f"⚠️ Longueur de lettre hors bornes attendues : {nb_mots} mots.")

        return resultat

    except Exception as e:
        print(f"⚠️ Erreur Groq API : {e}")
        return None
