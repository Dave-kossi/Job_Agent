import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

MOTS_CLES_PAR_DEFAUT = [
    "Stage Data Science", "Alternance Data Science",
    "Stage Machine Learning", "Alternance Machine Learning",
    "Stage Intelligence Artificielle", "Alternance Intelligence Artificielle",
]


# ==========================================
# CONFIG DÉCLARATIVE — ajouter une entreprise = ajouter une entrée ici
# ==========================================
def _config_airbus():
    return {
        "nom": "Airbus",
        "site_label": "Airbus Careers",
        "method": "GET",
        "url": "https://ag.jobs2web.com/api/search",
        "params_builder": lambda mot_cle, limite: {
            "q": mot_cle, "locationFacet": "France", "pageSize": limite
        },
        "jobs_path": ["jobs"],
        "mapper": lambda job: {
            "title": job.get("title", "Offre sans titre"),
            "location": job.get("location", "France"),
            "description": job.get("description", "Voir offre sur le site Airbus"),
            "job_url": job.get("url", ""),
        },
    }


def _config_societe_generale():
    return {
        "nom": "Société Générale",
        "site_label": "Société Générale Careers",
        "method": "GET",
        "url": "https://careers.societegenerale.com/api/offers",
        "params_builder": lambda mot_cle, limite: {
            "keywords": mot_cle, "languages": "fr", "limit": limite
        },
        "jobs_path": ["offers"],
        "mapper": lambda job: {
            "title": job.get("title", "Offre sans titre"),
            "location": job.get("city", "France"),
            "description": job.get("summary") or job.get("title", ""),
            "job_url": f"https://careers.societegenerale.com/offres-d-emploi/{job.get('slug', '')}",
        },
    }


def _config_bnp_paribas():
    return {
        "nom": "BNP Paribas",
        "site_label": "BNP Paribas Careers",
        "method": "GET",
        "url": "https://api.smartrecruiters.com/v1/companies/BNPParibas/postings",
        "params_builder": lambda mot_cle, limite: {"q": mot_cle, "limit": limite},
        "jobs_path": ["content"],
        "mapper": lambda job: {
            "title": job.get("name", "Offre sans titre"),
            "location": (job.get("location") or {}).get("city", "France"),
            "description": f"Offre BNP Paribas : {job.get('name', '')}",
            "job_url": f"https://jobs.smartrecruiters.com/BNPParibas/{job.get('id', '')}",
        },
    }


def _config_eiffage():
    return {
        "nom": "Eiffage",
        "site_label": "Eiffage Careers",
        "method": "GET",
        "url": "https://job.eiffage.com/api/jobs",
        # Pas de "type": "Stage" en dur ici — sinon l'API elle-même exclut
        # l'alternance avant même que le filtre Python n'intervienne.
        "params_builder": lambda mot_cle, limite: {"keyword": mot_cle, "limit": limite},
        "jobs_path": ["jobs"],
        "mapper": lambda job: {
            "title": job.get("title", "Offre sans titre"),
            "location": job.get("location", "France"),
            "description": job.get("description", f"Offre chez Eiffage : {job.get('title', '')}"),
            "job_url": job.get("url", ""),
        },
    }


CONFIGS_REST_SIMPLE = [
    _config_airbus(),
    _config_societe_generale(),
    _config_bnp_paribas(),
    _config_eiffage(),
]


def _extraire_jobs(data: dict, jobs_path: list) -> list:
    for cle in jobs_path:
        if not isinstance(data, dict):
            return []
        data = data.get(cle, [])
    return data if isinstance(data, list) else []


def _collecter_source_rest(config: dict, mots_cles: list, limite: int) -> list:
    """Interroge une entreprise dont l'API suit un pattern GET simple
    (query params + JSON de jobs). Thales (Workday, payload POST complexe)
    n'entre pas dans ce moule et reste géré à part."""
    offres = []
    for mot_cle in mots_cles:
        try:
            params = config["params_builder"](mot_cle, limite)
            res = requests.get(config["url"], params=params, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ {config['nom']} status {res.status_code} pour '{mot_cle}'")
                continue

            jobs = _extraire_jobs(res.json(), config["jobs_path"])
            for job in jobs:
                offre = config["mapper"](job)
                offre["site"] = config["site_label"]
                offre["company"] = config["nom"]
                offres.append(offre)
        except Exception as e:
            print(f"⚠️ Erreur {config['nom']} pour '{mot_cle}' : {e}")
    return offres


def _collecter_thales(mots_cles: list, limite: int) -> list:
    """Cas à part : Workday attend un payload POST structuré, pas des
    query params classiques."""
    offres = []
    url_thales = "https://thales.wd3.myworkdayjobs.com/wday/cxs/thales/Careers/jobs"
    for mot_cle in mots_cles:
        try:
            payload = {
                "appliedFacets": {"locationCountry": ["f2e609fc29784ca1b80f12713d16f06d"]},
                "limit": limite,
                "searchText": mot_cle
            }
            res = requests.post(url_thales, json=payload, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ Thales status {res.status_code} pour '{mot_cle}'")
                continue

            for job in res.json().get('jobPostings', []):
                offres.append({
                    "site": "Thales Workday",
                    "company": "Thales",
                    "title": job.get('title', 'Offre sans titre'),
                    "location": job.get('locationHierarchy', 'France'),
                    "description": f"Poste chez Thales : {job.get('title', '')}",
                    "job_url": "https://thales.wd3.myworkdayjobs.com/en-US/Careers" + job.get('externalPath', '')
                })
        except Exception as e:
            print(f"⚠️ Erreur Thales pour '{mot_cle}' : {e}")
    return offres


# ==========================================
# COLLECTE GLOBALE DES GRANDS GROUPES
# ==========================================
def collecter_offres_grands_groupes(mots_cles: list = None, limite: int = 5) -> list:
    """
    Interroge les endpoints carrières publics des grands groupes
    (Airbus, Thales, Société Générale, BNP Paribas, Eiffage) pour
    chaque mot-clé stage/alternance fourni.
    """
    mots_cles = mots_cles or MOTS_CLES_PAR_DEFAUT
    offres_totales = []

    for config in CONFIGS_REST_SIMPLE:
        offres_totales.extend(_collecter_source_rest(config, mots_cles, limite))

    offres_totales.extend(_collecter_thales(mots_cles, limite))

    return offres_totales
