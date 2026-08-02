import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from jobspy import scrape_jobs

# ==========================================
# 1. PARAMÈTRES DE RECHERCHE CIBLÉS
# ==========================================
SEARCH_TERMS = [
    # Français
    "Stage Data Scientist",
    "Stage Data Science",
    "Stage Intelligence Artificielle",
    "Stage IA Generative",
    "Stage Machine Learning",
    "Stage Data Engineer",
    "Stage LLM",
    # Anglais
    "Data Scientist Intern",
    "Data Science Internship",
    "Machine Learning Intern",
    "AI Intern",
    "LLM Intern",
    "Generative AI Intern",
    "Data Engineer Intern",
    "Computer Vision Intern",
    "NLP Intern"
]

CITIES = [
    "Paris, France",
    "Lyon, France",
    "Toulouse, France",
    "Lille, France",
    "Nantes, France",
    "Bordeaux, France",
    "Grenoble, France",
    "Sophia Antipolis, France",
    "Strasbourg, France",
    "Mulhouse, France",
    "Marseille, France",
    "Montpellier, France",
    "Rennes, France",
    "Nice, France",
    "Remote"
]

# ==========================================
# 2. SCRAPER WELCOME TO THE JUNGLE (API)
# ==========================================
def collecter_offres_wttj(recherche: str, limite: int = 5) -> list:
    """Récupère les offres sur Welcome to the Jungle via leur API publique."""
    url = f"https://www.welcometothejungle.com/api/v1/jobs?query={recherche}&per_page={limite}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    offres = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            for job in response.json().get('jobs', []):
                org = job.get('organization', {})
                job_slug = job.get('slug', '')
                org_slug = org.get('slug', '')

                job_url = (
                    f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{job_slug}"
                    if org_slug and job_slug else ""
                )

                offres.append({
                    "site": "Welcome to the Jungle",
                    "company": org.get('name', 'Inconnue'),
                    "title": job.get('name', 'Sans titre'),
                    "location": job.get('office', {}).get('city', 'France'),
                    "description": (job.get('profile', '') or '') + "\n\n" + (job.get('description', '') or ''),
                    "job_url": job_url
                })
    except Exception as e:
        print(f"⚠️ Erreur WTTJ ({recherche}) : {e}")

    return offres

# ==========================================
# 3. SCRAPER STAGE.FR
# ==========================================
def collecter_offres_stage_fr(limite: int = 5) -> pd.DataFrame:
    """Scrape les offres de stage en Data Science / ML / IA sur Stage.fr."""
    offres = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    termes_cibles = ["Data Science", "Machine Learning", "Intelligence Artificielle", "Data Scientist"]

    for kw in termes_cibles:
        print(f"🔎 Check Stage.fr : '{kw}'")
        query = kw.replace(" ", "+")
        url = f"https://www.stage.fr/offres?q={query}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                cartes = soup.select(".job-card, .offre-item, article")[:limite]
                
                for carte in cartes:
                    titre_elem = carte.select_one(".job-title, h3, .title")
                    entreprise_elem = carte.select_one(".company-name, .company, .entreprise")
                    link_elem = carte.select_one("a[href]")
                    
                    if titre_elem and link_elem:
                        href = link_elem["href"]
                        job_url = href if href.startswith("http") else f"https://www.stage.fr{href}"
                        
                        offres.append({
                            "site": "Stage.fr",
                            "company": entreprise_elem.text.strip() if entreprise_elem else "Inconnue",
                            "title": titre_elem.text.strip(),
                            "location": "France",
                            "description": f"Stage {titre_elem.text.strip()} - Recherche Data/IA",
                            "job_url": job_url
                        })
        except Exception as e:
            print(f"⚠️ Erreur Stage.fr pour '{kw}' : {e}")
            
    return pd.DataFrame(offres)

# ==========================================
# 4. FONCTION PRINCIPALE APPELÉE PAR MAIN.PY
# ==========================================
def collecter_offres(recherche=None, localisation=None, limites=5) -> pd.DataFrame:
    """
    Parcourt les combinaisons de mots-clés et de villes sur :
    - JobSpy (LinkedIn, Indeed, Google)
    - Welcome to the Jungle
    - Stage.fr
    """
    toutes_les_offres = []

    termes_a_chercher = [recherche] if recherche else SEARCH_TERMS[:4]
    villes_a_chercher = [localisation] if localisation else CITIES[:4]

    print(f"\n🌐 Lancement de la collecte globale sur {len(termes_a_chercher)} termes et {len(villes_a_chercher)} zones...")

    # 1. JobSpy (LinkedIn, Indeed, Google)
    for term in termes_a_chercher:
        for city in villes_a_chercher:
            print(f"🔎 Check JobSpy : '{term}' à '{city}'")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "google"],
                    search_term=term,
                    location=city,
                    results_wanted=limites,
                    hours_old=72,
                    country_indeed='France'
                )
                if not jobs.empty:
                    toutes_les_offres.append(jobs)
            except Exception as e:
                print(f"⚠️ Erreur JobSpy ({term} - {city}) : {e}")

            time.sleep(1)

    # 2. Welcome to the Jungle
    for term in termes_a_chercher:
        print(f"🔎 Check WTTJ : '{term}'")
        offres_wttj = collecter_offres_wttj(recherche=term, limite=limites)
        if offres_wttj:
            toutes_les_offres.append(pd.DataFrame(offres_wttj))

    # 3. Stage.fr
    df_stage = collecter_offres_stage_fr(limite=limites)
    if not df_stage.empty:
        toutes_les_offres.append(df_stage)

    # 4. Fusion et nettoyage
    if toutes_les_offres:
        df_final = pd.concat(toutes_les_offres, ignore_index=True)
        df_final = df_final.dropna(subset=['job_url'])
        df_final = df_final.drop_duplicates(subset=['job_url'], keep='first')
        
        print(f" Total : {len(df_final)} offres uniques récupérées.")
        return df_final
    else:
        print(" Aucune offre trouvée.")
        return pd.DataFrame()
