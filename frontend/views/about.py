"""Page « A propos » : documentation rapide et pistes d'evolution."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.markdown("## À propos de DataFrance Explorer")
    st.caption("Prototype open source construit sur l'API publique de data.gouv.fr.")

    st.markdown(
        """
        ### Le projet

        **DataFrance Explorer** est un premier jet d'explorateur de données publiques
        françaises. Il interroge l'API officielle [data.gouv.fr](https://www.data.gouv.fr)
        et propose :

        - un **tableau de bord** avec les volumes et répartitions globales ;
        - une **recherche en direct** (résultats pendant la frappe) par mot-clé,
          format, producteur et licence ;
        - une **fiche détaillée** pour chaque jeu de données ;
        - un **aperçu des fichiers** tabulaires (CSV, JSON, Excel, Parquet) ;
        - des **filtres locaux** par plage numérique, période ou modalités ;
        - des **graphiques automatiques** (distributions, catégories, séries temporelles),
          une **carte interactive** si des coordonnées sont détectées ;
        - un **profil statistique** des colonnes et une matrice de corrélations ;
        - un **annuaire des organisations** productrices.

        ### Architecture

        ```
        data.gouv.fr (API v2)
                 │
                 ▼
        ┌─────────────────────────┐      HTTP/JSON      ┌──────────────────────┐
        │  Backend FastAPI        │ ◄─────────────────► │  Frontend Streamlit  │
        │  · proxy + cache TTL    │                     │  · header / footer   │
        │  · normalisation        │                     │  · pages & composants│
        │  · pandas (aperçu/profil)│                     │  · Plotly            │
        └─────────────────────────┘                     └──────────────────────┘
        ```

        Le backend télécharge et lit les fichiers côté serveur : le navigateur ne
        reçoit que les lignes nécessaires à l'affichage. Les fichiers Parquet
        pré-calculés par data.gouv.fr sont utilisés en priorité lorsqu'ils existent.

        ### Endpoints principaux

        | Méthode | Route | Description |
        |---|---|---|
        | `GET` | `/api/health` | état du service |
        | `GET` | `/api/stats/overview` | chiffres clés + facettes |
        | `GET` | `/api/search/datasets` | recherche de jeux de données |
        | `GET` | `/api/search/organizations` | recherche d'organisations |
        | `GET` | `/api/datasets/{id}` | fiche complète + ressources |
        | `GET` | `/api/datasets/{id}/preview` | aperçu d'une ressource |
        | `GET` | `/api/datasets/{id}/profile` | profil statistique |
        | `GET` | `/api/organizations/{id}` | fiche organisation |

        Documentation interactive complète : [`/docs`](http://127.0.0.1:8000/docs).

        ### Personnaliser le template

        1. **Ajouter une page** : créez `frontend/views/ma_page.py` avec une fonction
           `render()`, puis ajoutez-la au dictionnaire `PAGES` dans `frontend/app.py`.
        2. **Ajouter un composant** : placez-le dans `frontend/components/` et
           réutilisez la charte CSS définie dans `frontend/styles.py`.
        3. **Ajouter un endpoint** : créez un routeur dans
           `backend/app/api/routes/`, ajoutez un modèle dans
           `backend/app/schemas.py`, puis incluez le routeur dans `backend/app/main.py`.

        ### Limites de cette première version

        - L'aperçu et le profil sont limités en taille (25 Mo par fichier par défaut,
          20 000 lignes analysées) pour protéger le serveur.
        - Les fichiers très volumineux ou exotiques (XML complexes, archives ZIP)
          ne sont pas encore pris en charge.
        - Le cache est en mémoire : il est perdu au redémarrage du backend.
        - Les charts sont générés automatiquement à partir des types détectés :
          ils restent volontairement simples.
        - Les filtres locaux et la carte portent sur les lignes chargées dans
          l'aperçu, pas sur l'intégralité du fichier distant.

        ### Pistes pour la suite

        - Export des visualisations en PNG / CSV et partage de vues par URL.
        - Filtres combinés persistants et cartographie GeoJSON (contours, choroplèthes).
        - Cache persistant (Redis) et déploiement Docker.
        - Comparaison de plusieurs jeux de données.
        """
    )

    st.info(
        "Interface non officielle. Les données affichées restent soumises aux licences "
        "et conditions de réutilisation définies par chaque producteur."
    )
