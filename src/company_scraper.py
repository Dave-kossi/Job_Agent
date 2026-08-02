import requests
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

KEYWORDS_DATA = [
    "Stage Data Science",
    "Stage Machine Learning",
    "Stage Intelligence Artificielle",
    "Stage AI",
    "Stage Data Engineer"
]


# ==========================================
# 1. SCRAPER SPÉCIFIQUE EIFFAGE
# ==========================================
def collecter_offres_eiffage(limite: int = 5) -> list:
    """
    Collecte les offres de stage en Data Science / ML / IA directement depuis le portail Eiffage.
    """
    offres_eiffage = []
    print("🔍 Check Eiffage Carrières...")

    url_api = "https://job.eiffage.com/api/jobs"

    for kw in KEYWORDS_DATA:
        params = {
            "keyword": kw,
            "limit": limite,
            "type": "Stage"
        }
        try:
            res = requests.get(url_api, params=params, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("jobs", []):
                    offres_eiffage.append({
                        "site": "Eiffage Careers",
                        "company": "Eiffage",
                        "title": item.get("title", "Offre sans titre"),
                        "location": item.get("location", "France"),
                        "description": item.get("description", f"Stage chez Eiffage : {item.get('title')}"),
                        "job_url": item.get("url", "")
                    })
        except Exception as e:
            print(f"⚠️ Erreur Eiffage pour '{kw}' : {e}")

    return offres_eiffage


# ==========================================
# 2. COLLECTE GLOBALE DES GRANDS GROUPES
# ==========================================
def collecter_offres_grands_groupes(mot_cle="Stage Data Science", limite=5) -> list:
    """
    Interroge directement les endpoints carrières publics des grands groupes industriels et bancaires :
    Airbus, Thales, Société Générale, BNP Paribas et Eiffage.
    """
    offres_totales = []

    # 1. AIRBUS
    try:
        url_airbus = f"https://ag.jobs2web.com/api/search?q={mot_cle}&locationFacet=France&pageSize={limite}"
        res = requests.get(url_airbus, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobs', []):
                offres_totales.append({
                    "site": "Airbus Careers",
                    "company": "Airbus",
                    "title": job.get('title'),
                    "location": job.get('location', 'France'),
                    "description": job.get('description', 'Voir offre sur le site Airbus'),
                    "job_url": job.get('url')
                })
    except Exception as e:
        print(f"⚠️ Erreur Airbus : {e}")

    # 2. THALES
    try:
        url_thales = "https://thales.wd3.myworkdayjobs.com/wday/cxs/thales/Careers/jobs"
        payload = {
            "appliedFacets": {"locationCountry": ["f2e609fc29784ca1b80f12713d16f06d"]},
            "limit": limite,
            "searchText": mot_cle
        }
        res = requests.post(url_thales, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobPostings', []):
                offres_totales.append({
                    "site": "Thales Workday",
                    "company": "Thales",
                    "title": job.get('title'),
                    "location": job.get('locationHierarchy', 'France'),
                    "description": f"Poste chez Thales : {job.get('title')}",
                    "job_url": "https://thales.wd3.myworkdayjobs.com/en-US/Careers" + job.get('externalPath', '')
                })
    except Exception as e:
        print(f"⚠️ Erreur Thales : {e}")

    # 3. SOCIÉTÉ GÉNÉRALE
    try:
        url_sg = f"https://careers.societegenerale.com/api/offers?keywords={mot_cle}&languages=fr&limit={limite}"
        res = requests.get(url_sg, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('offers', []):
                offres_totales.append({
                    "site": "Société Générale Careers",
                    "company": "Société Générale",
                    "title": job.get('title'),
                    "location": job.get('city', 'France'),
                    "description": job.get('summary', '') or job.get('title'),
                    "job_url": f"https://careers.societegenerale.com/offres-d-emploi/{job.get('slug', '')}"
                })
    except Exception as e:
        print(f"⚠️ Erreur Société Générale : {e}")

    # 4. BNP PARIBAS
    try:
        url_bnp = f"https://api.smartrecruiters.com/v1/companies/BNPParibas/postings?q={mot_cle}&limit={limite}"
        res = requests.get(url_bnp, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('content', []):
                offres_totales.append({
                    "site": "BNP Paribas Careers",
                    "company": "BNP Paribas",
                    "title": job.get('name'),
                    "location": job.get('location', {}).get('city', 'France'),
                    "description": f"Offre BNP Paribas : {job.get('name')}",
                    "job_url": f"https://jobs.smartrecruiters.com/BNPParibas/{job.get('id')}"
                })
    except Exception as e:
        print(f"⚠️ Erreur BNP Paribas : {e}")

    # 5. EIFFAGE (Nouveau)
    offres_eiffage = collecter_offres_eiffage(limite=limite)
    offres_totales.extend(offres_eiffage)

    return offres_totales
