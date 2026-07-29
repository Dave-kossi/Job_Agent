# 🤖 Job Agent AI - Assistant de Recherche de Stages & Emplois

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-green.svg)](https://github.com/Dave-kossi/Job_Agent/actions)

**Job Agent AI** est un assistant automatisé intelligent conçu pour scraper, analyser et filtrer quotidiennement des offres de stages et d'emplois en fonction d'un profil candidat (CV, compétences, portfolio).

L'agent s'exécute automatiquement en arrière-plan plusieurs fois par jour grâce à **GitHub Actions**, utilise **Groq (LLM)** pour évaluer la pertinence des offres, et affiche les meilleures opportunités sur une interface web mobile-friendly via **Streamlit**.

---

##  Fonctionnalités Principales

* 🔍 **Scraping Automatisé :** Récupération périodique d'offres sur les plateformes cibles.
* 🧠 **Analyse IA par Groq :** Comparaison intelligente entre les exigences de l'offre et le profil du candidat (`data/cv.pdf`).
* 📊 **Score de Pertinence :** Attribution d'une note de compatibilité et résumé synthétique pour chaque offre.
* ⏰ **Automatisation Cron (GitHub Actions) :** Exécution autonome du script 4 fois par jour sans intervention humaine.
* 📱 **Interface Dashboard (Streamlit) :** Consultation facile des opportunités depuis PC ou smartphone.

---

## 🛠️ Architecture du Projet

```text
Job_Agent/
├── .github/
│   └── workflows/
│       └── agent_cron.yml   # Automation GitHub Actions (Cron job)
├── data/
│   ├── cv.pdf              # CV pour le matching IA
│   ├── portfolio.html      # Projets & portfolio du candidat
│   └── historique.json     # Base de données des offres trouvées
├── src/
│   ├── agent.py            # Logique d'analyse Groq / LLM
│   ├── scraper.py          # Modules de scraping d'offres
│   ├── parser.py           # Extraction de texte (PDF, HTML)
│   └── company_scraper.py  # Scraping ciblé par entreprises
├── .gitignore              # Fichiers à ignorer par Git
├── app.py                  # Application Dashboard Streamlit
├── main.py                 # Script principal (pipeline complet)
├── README.md               # Documentation du projet
└── requirements.txt        # Dépendances Python
