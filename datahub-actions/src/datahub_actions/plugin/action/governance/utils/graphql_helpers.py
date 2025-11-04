# Copyright 2021 Acryl Data, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# GraphQL query to fetch entity metadata for governance checks
# See: https://datahubproject.io/docs/graphql/overview
ENTITY_METADATA_QUERY = """
query getEntityMetadata($urn: String!) {
  entity(urn: $urn) {
    urn
    type
    ... on Dataset {
      platform {
        name
      }
      properties {
        description
      }
      editableProperties {
        description
      }
      ownership {
        owners {
          owner {
            ... on CorpUser {
              urn
            }
            ... on CorpGroup {
              urn
            }
          }
          type
        }
      }
      globalTags {
        tags {
          tag {
            urn
            name
          }
        }
      }
      glossaryTerms {
        terms {
          term {
            urn
            name
          }
        }
      }
    }
    ... on Dashboard {
      platform {
        name
      }
      properties {
        description
      }
      editableProperties {
        description
      }
      ownership {
        owners {
          owner {
            ... on CorpUser {
              urn
            }
            ... on CorpGroup {
              urn
            }
          }
          type
        }
      }
      globalTags {
        tags {
          tag {
            urn
            name
          }
        }
      }
      glossaryTerms {
        terms {
          term {
            urn
            name
          }
        }
      }
    }
    ... on Chart {
      platform {
        name
      }
      properties {
        description
      }
      editableProperties {
        description
      }
      ownership {
        owners {
          owner {
            ... on CorpUser {
              urn
            }
            ... on CorpGroup {
              urn
            }
          }
          type
        }
      }
      globalTags {
        tags {
          tag {
            urn
            name
          }
        }
      }
      glossaryTerms {
        terms {
          term {
            urn
            name
          }
        }
      }
    }
    ... on DataJob {
      properties {
        description
      }
      editableProperties {
        description
      }
      ownership {
        owners {
          owner {
            ... on CorpUser {
              urn
            }
            ... on CorpGroup {
              urn
            }
          }
          type
        }
      }
      globalTags {
        tags {
          tag {
            urn
            name
          }
        }
      }
      glossaryTerms {
        terms {
          term {
            urn
            name
          }
        }
      }
    }
  }
}
"""


def fetch_entity_metadata(graph: Any, entity_urn: str) -> Optional[Dict[str, Any]]:
    """
    Fetch entity metadata using GraphQL for governance checks.

    Args:
        graph: DataHub graph client with get_by_graphql_query capability
        entity_urn: URN of the entity to fetch

    Returns:
        Dictionary containing entity metadata, or None if fetch fails

    See: https://datahubproject.io/docs/api/graphql/overview
    """
    try:
        result = graph.get_by_graphql_query(
            {
                "query": ENTITY_METADATA_QUERY,
                "variables": {"urn": entity_urn},
            }
        )

        if not result:
            logger.warning(f"No data returned for entity: {entity_urn}")
            return None

        entity_data = result.get("entity")
        if not entity_data:
            logger.warning(f"Entity not found: {entity_urn}")
            return None

        # Normalize the entity data structure
        metadata = {
            "urn": entity_data.get("urn"),
            "type": entity_data.get("type"),
            "platform": entity_data.get("platform"),
            "properties": entity_data.get("properties"),
            "editableProperties": entity_data.get("editableProperties"),
            "ownership": _normalize_ownership(entity_data.get("ownership")),
            "globalTags": entity_data.get("globalTags"),
            "glossaryTerms": _normalize_glossary_terms(entity_data.get("glossaryTerms")),
        }

        return metadata

    except Exception as e:
        logger.error(f"Failed to fetch metadata for {entity_urn}: {e}", exc_info=True)
        return None


def _normalize_ownership(ownership: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize ownership structure to extract owner URNs.

    The GraphQL response has nested structure:
    owners[].owner.urn - need to flatten this.
    """
    if not ownership:
        return None

    owners = ownership.get("owners", [])
    if not owners:
        return ownership

    normalized_owners = []
    for owner_entry in owners:
        owner_obj = owner_entry.get("owner")
        if owner_obj:
            normalized_owners.append({
                "owner": owner_obj.get("urn"),
                "type": owner_entry.get("type"),
            })

    return {
        "owners": normalized_owners,
    }


def _normalize_glossary_terms(glossary_terms: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize glossary terms structure to extract term URNs and names.

    The GraphQL response has nested structure:
    terms[].term.urn - need to flatten this.
    """
    if not glossary_terms:
        return None

    terms = glossary_terms.get("terms", [])
    if not terms:
        return glossary_terms

    normalized_terms = []
    for term_entry in terms:
        term_obj = term_entry.get("term")
        if term_obj:
            normalized_terms.append({
                "urn": term_obj.get("urn"),
                "name": term_obj.get("name"),
            })

    return {
        "terms": normalized_terms,
    }
