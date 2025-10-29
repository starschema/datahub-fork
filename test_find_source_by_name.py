"""
Utility to resolve the exact ingestion source (connector) used for a dataset,
given a human table name like DEMOGRAPHICS. No SQLAlchemy; uses native selection.

Usage:
  python test_find_source_by_name.py DEMOGRAPHICS [--platform snowflake] [--env PROD]

ENV:
  DATAHUB_GMS_URL (default: http://datahub-gms:8080)
"""

import argparse
import os
import re
from typing import List

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig

from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.data_quality.connector_registry import (
    ConnectorRegistry,
)


def _graphql_search(graph: DataHubGraph, query: str, entity: str = "DATASET", start: int = 0, count: int = 25):
    url = f"{graph._gms_server}/api/graphql"
    payload = {
        "query": """
query search($input: SearchInput!) {
  search(input: $input) {
    start
    count
    total
    searchResults {
      entity { urn }
    }
  }
}
""",
        "variables": {
            "input": {
                "type": entity,
                "query": query,
                "start": start,
                "count": count,
                "filters": [],
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-DataHub-Actor": "urn:li:corpuser:datahub",
    }
    resp = graph._session.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data.get("search", {})


def _filter_urns_by_table(urns: List[str], table_name: str, platform: str | None, env: str | None) -> List[str]:
    results = []
    name_upper = table_name.upper()
    for urn in urns:
        if platform and f"dataPlatform:{platform.lower()}" not in urn.lower():
            continue
        # URN format: urn:li:dataset:(urn:li:dataPlatform:PLATFORM,DB.SCHEMA.TABLE,ENV)
        try:
            name_part = urn.split(",")[1]
            env_part = urn.split(",")[-1].rstrip(")")
            if env and env_part.upper() != env.upper():
                continue
            # Match last token of the name_part against table
            table_token = name_part.split(".")[-1]
            if table_token.upper() == name_upper:
                results.append(urn)
        except Exception:
            continue
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("table", help="Table name, e.g. DEMOGRAPHICS")
    parser.add_argument("--platform", default=None, help="Optional platform filter, e.g. snowflake")
    parser.add_argument("--env", default=None, help="Optional env filter, e.g. PROD")
    args = parser.parse_args()

    gms = os.getenv("DATAHUB_GMS_URL", "http://datahub-gms:8080")
    graph = DataHubGraph(config=DatahubClientConfig(server=gms))

    # 1) Search for candidate dataset urns by table name
    search = _graphql_search(graph, args.table, entity="DATASET", start=0, count=50)
    urns = [r["entity"]["urn"] for r in search.get("searchResults", [])]
    urns = _filter_urns_by_table(urns, args.table, args.platform, args.env)

    if not urns:
        print(f"No datasets found matching table '{args.table}' (platform={args.platform} env={args.env})")
        return

    print(f"Found {len(urns)} candidate dataset(s):")
    for u in urns:
        print(f" - {u}")

    # 2) Resolve exact ingestion source for each candidate and print selection
    acryl_graph = AcrylDataHubGraph(baseGraph=graph)
    registry = ConnectorRegistry({}, graph=acryl_graph)

    for u in urns:
        src = registry.find_ingestion_source_for_dataset(u)
        if src:
            print(
                f"\nDataset: {u}\nSelected source: name={src.get('name')} urn={src.get('urn')} type={src.get('type')}"
            )
        else:
            print(f"\nDataset: {u}\nSelected source: <none>")


if __name__ == "__main__":
    main()

