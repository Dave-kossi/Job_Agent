import requests

def lire_profil_github(username: str) -> str:
    """
    Fetches public repository details from a GitHub profile to feed to the LLM.
    """
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)   
        if response.status_code == 200:
            repos = response.json()
            resume_github = f"--- PROFIL GITHUB DE ({username}) ---\n"
            
            for repo in repos:
                # Filter out forks to only keep original projects
                if not repo.get('fork'):
                    nom = repo.get('name')
                    description = repo.get('description', 'Pas de description')
                    langage = repo.get('language', 'Non spécifié')
                    stars = repo.get('stargazers_count', 0)
                    
                    resume_github += f"- Projet : {nom}\n"
                    resume_github += f"  Langage principal : {langage}\n"
                    resume_github += f"  Description : {description}\n"
                    resume_github += f"  Étoiles : {stars}\n\n"
                    
            return resume_github
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération GitHub : {e}")
        
    return "Aucune donnée GitHub récupérée."