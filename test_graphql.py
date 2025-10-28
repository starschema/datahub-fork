import json
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig

config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)

# Exact query from action_graph.py lines 138-170
query = {
    "query": """
query listIngestionSources($input: ListIngestionSourcesInput!, $execution_start: Int!, $execution_count: Int!) {
  listIngestionSources(input: $input) {
    start
    count
    total
    ingestionSources {
      urn
      type
      name
      config {
        recipe
      }
      executions(start: $execution_start, count: $execution_count) {
        start
        count
        total
        executionRequests {
          urn
        }
      }
    }
  }
}
""",
    "variables": {
        "input": {"start": 0, "count": 10},
        "execution_start": 0,
        "execution_count": 10,
    },
}

url = f'{graph._gms_server}/api/graphql'
headers = {
    'X-DataHub-Actor': 'urn:li:corpuser:admin',
    'Content-Type': 'application/json',
}

response = graph._session.post(url, data=json.dumps(query), headers=headers)
print(f'Status: {response.status_code}')
print(f'\nFull Response:\n{json.dumps(response.json(), indent=2)}')

# Also test what get_by_graphql_query returns
print(f'\nExtracted data field:')
json_resp = response.json()
data = json_resp.get('data', {})
print(json.dumps(data, indent=2))
