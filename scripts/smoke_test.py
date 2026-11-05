"""Smoke test manuel du backend DataFrance Explorer.

Usage :
    python scripts/smoke_test.py [http://127.0.0.1:8000]
"""

from __future__ import annotations

import sys

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def get(path: str, **params: object) -> dict:
    response = requests.get(f"{BASE}{path}", params=params, timeout=180)
    response.raise_for_status()
    return response.json()


def main() -> int:
    health = get("/api/health", deep="true")
    print(f"[ok] health       {health.get('status')} ({health.get('upstream_latency_ms')} ms)")

    stats = get("/api/stats/overview")
    totals = stats["totals"]
    print(
        "[ok] overview     "
        f"{totals['datasets']} datasets, {totals['organizations']} organisations, "
        f"{totals['reuses']} reutilisations, {totals['dataservices']} services"
    )
    print(f"     facettes     {', '.join(stats['facets'])}")

    search = get("/api/search/datasets", q="transport", page_size=10)
    print(f"[ok] recherche    {search['total']} resultats, {len(search['data'])} renvoyes")
    if not search["data"]:
        print("[!!] aucun resultat de recherche")
        return 1

    dataset = search["data"][0]
    detail: dict = {}
    tabular: list[dict] = []
    for candidate in search["data"]:
        detail = get(f"/api/datasets/{candidate['id']}")
        tabular = [resource for resource in detail["resources"] if resource["is_tabular"]]
        if tabular:
            dataset = candidate
            break

    print(f"     exemple      {dataset['title'][:70]} — {dataset['resources_count']} fichier(s)")
    print(
        f"[ok] detail       {len(detail.get('resources', []))} ressources, "
        f"{len(tabular)} tabulaires"
    )

    if tabular:
        resource_id = tabular[0]["id"]
        preview = get(
            f"/api/datasets/{dataset['id']}/preview",
            resource_id=resource_id,
            limit=5,
        )
        print(
            f"[ok] apercu       {preview['rows_loaded']} lignes, "
            f"{len(preview['columns'])} colonnes ({preview['source']})"
        )
        profile = get(
            f"/api/datasets/{dataset['id']}/profile",
            resource_id=resource_id,
            limit=1000,
        )
        print(
            f"[ok] profil       {profile['rows_analyzed']} lignes analysees, "
            f"correlation={'oui' if profile['correlation'] else 'non'}"
        )

    organizations = get("/api/search/organizations", q="biodiversite", page_size=2)
    if organizations["data"]:
        organization = get(f"/api/organizations/{organizations['data'][0]['id']}")
        organization_name = organization["organization"]["name"]
        print(
            f"[ok] organisation {organization_name} — "
            f"{organization['datasets_total']} datasets"
        )

    print("\nSmoke test termine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
