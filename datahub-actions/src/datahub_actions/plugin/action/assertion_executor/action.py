# Copyright 2021 Acryl Data, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    AssertionRunEventClass,
    AssertionRunStatusClass,
    MetadataChangeLogClass as MetadataChangeLog,
)
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.assertion_executor.config import AssertionExecutorConfig
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class AssertionExecutorAction(Action):
    """
    DataHub Action that automatically executes assertions when datasets are ingested or profiled.

    This action:
    1. Listens for dataset ingestion (status aspect) and profile updates (datasetProfile aspect)
    2. Queries all assertions linked to the dataset
    3. Filters assertions by trigger type (ON_INGESTION, ON_PROFILE, SCHEDULED)
    4. Executes SQL assertions using the correct connector (from ingestion source mapping)
    5. Emits AssertionRunEvent results back to DataHub
    """

    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> "Action":
        action_config = AssertionExecutorConfig.model_validate(config_dict or {})
        logger.info("Assertion Executor Action initialized")
        return cls(action_config, ctx)

    def __init__(self, config: AssertionExecutorConfig, ctx: PipelineContext):
        self.config = config
        self.ctx = ctx

        if not ctx.graph:
            raise ValueError("DataHub graph client is required for Assertion Executor Action")

        # Initialize connector registry for database connections
        connector_configs_dict = config.connector_configs or {}
        self.connector_registry = ConnectorRegistry(
            connector_configs_dict,
            graph=ctx.graph,
        )

    def act(self, event: EventEnvelope) -> None:
        """
        Process incoming DataHub events and execute assertions.

        Listens for:
        - MetadataChangeLogEvent_v1 with status aspect (ingestion events)
        - MetadataChangeLogEvent_v1 with datasetProfile aspect (profile events)
        """
        if not self.config.enabled:
            logger.debug("Assertion Executor is disabled, skipping event")
            return

        try:
            dataset_urn = None
            trigger_type = None

            # Handle MetadataChangeLog events
            if event.event_type == "MetadataChangeLogEvent_v1":
                assert isinstance(event.event, MetadataChangeLog)
                mcl: MetadataChangeLog = event.event

                # Only process dataset entities
                if mcl.entityType != "dataset":
                    logger.debug(f"Skipping non-dataset MCL: {mcl.entityType}")
                    return

                dataset_urn = mcl.entityUrn

                # Check aspect type to determine trigger
                if mcl.aspectName == "status" and self.config.trigger_on_ingestion:
                    trigger_type = "ON_INGESTION"
                    logger.info(
                        f"Processing ingestion event for: {dataset_urn}"
                    )
                elif mcl.aspectName == "datasetProfile" and self.config.trigger_on_profile:
                    trigger_type = "ON_PROFILE"
                    logger.info(
                        f"Processing profile update for: {dataset_urn}"
                    )
                else:
                    logger.debug(
                        f"Skipping aspect {mcl.aspectName} - not configured to trigger"
                    )
                    return

            else:
                logger.debug(
                    f"Skipping unsupported event type: {event.event_type}"
                )
                return

            # Execute assertions for this dataset and trigger type
            if dataset_urn and trigger_type:
                self._execute_assertions_for_dataset(dataset_urn, trigger_type)

        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)

    def _execute_assertions_for_dataset(
        self, dataset_urn: str, trigger_type: str
    ) -> None:
        """
        Query and execute all assertions for a dataset that match the trigger type.

        Args:
            dataset_urn: URN of the dataset
            trigger_type: Type of trigger (ON_INGESTION, ON_PROFILE, SCHEDULED)
        """
        try:
            # Query assertions for this dataset
            assertions = self._query_assertions(dataset_urn)

            if not assertions:
                logger.debug(f"No assertions found for {dataset_urn}")
                return

            logger.info(
                f"Found {len(assertions)} assertions for {dataset_urn}, "
                f"filtering by trigger type: {trigger_type}"
            )

            # Filter assertions by trigger type
            matching_assertions = [
                assertion for assertion in assertions
                if self._should_execute_assertion(assertion, trigger_type)
            ]

            if not matching_assertions:
                logger.debug(
                    f"No assertions match trigger type {trigger_type} for {dataset_urn}"
                )
                return

            logger.info(
                f"Executing {len(matching_assertions)} assertions for {dataset_urn}"
            )

            # Execute each assertion
            for assertion in matching_assertions:
                self._execute_single_assertion(assertion, dataset_urn)

        except Exception as e:
            logger.error(
                f"Error executing assertions for {dataset_urn}: {e}", exc_info=True
            )

    def _query_assertions(self, dataset_urn: str) -> List[Dict[str, Any]]:
        """
        Query all assertions linked to a dataset.

        Returns:
            List of assertion dictionaries containing urn, type, sqlAssertion, customProperties, etc.
        """
        try:
            # GraphQL query to get all assertions for the dataset
            query = """
            query getAssertions($urn: String!) {
                dataset(urn: $urn) {
                    assertions(start: 0, count: 100) {
                        total
                        assertions {
                            urn
                            info {
                                type
                                description
                                sqlAssertion {
                                    type
                                    statement
                                    operator
                                    parameters {
                                        value {
                                            value
                                            type
                                        }
                                        minValue {
                                            value
                                            type
                                        }
                                        maxValue {
                                            value
                                            type
                                        }
                                    }
                                }
                                source {
                                    type
                                }
                                customProperties {
                                    key
                                    value
                                }
                            }
                        }
                    }
                }
            }
            """

            result = self.ctx.graph.graph.execute_graphql(
                query, variables={"urn": dataset_urn}
            )

            if not result or "data" not in result:
                logger.warning(f"No data returned from GraphQL query for {dataset_urn}")
                return []

            dataset_data = result.get("data", {}).get("dataset")
            if not dataset_data:
                logger.debug(f"Dataset not found or no assertions: {dataset_urn}")
                return []

            assertions_data = dataset_data.get("assertions", {})
            assertions_list = assertions_data.get("assertions", [])

            logger.debug(
                f"Retrieved {len(assertions_list)} assertions for {dataset_urn}"
            )
            return assertions_list

        except Exception as e:
            logger.error(f"Error querying assertions for {dataset_urn}: {e}")
            return []

    def _should_execute_assertion(
        self, assertion: Dict[str, Any], trigger_type: str
    ) -> bool:
        """
        Check if assertion should be executed based on trigger type.

        Looks for 'assertionTrigger' in customProperties or defaults to ON_INGESTION
        for assertions with source.type = INFERRED (AI-generated).

        Args:
            assertion: Assertion dictionary from GraphQL
            trigger_type: Current trigger type (ON_INGESTION, ON_PROFILE)

        Returns:
            True if assertion should be executed
        """
        try:
            info = assertion.get("info", {})

            # Check source type
            source = info.get("source", {})
            source_type = source.get("type")

            # Get custom properties
            custom_props = info.get("customProperties", [])
            props_dict = {
                prop.get("key"): prop.get("value")
                for prop in custom_props
                if prop.get("key") and prop.get("value")
            }

            # Check for explicit trigger configuration
            assertion_triggers = props_dict.get("assertionTriggers", "").split(",")
            assertion_triggers = [t.strip() for t in assertion_triggers if t.strip()]

            if assertion_triggers:
                # Explicit triggers defined
                should_execute = trigger_type in assertion_triggers
                logger.debug(
                    f"Assertion {assertion.get('urn')} has triggers {assertion_triggers}, "
                    f"current trigger {trigger_type}, execute={should_execute}"
                )
                return should_execute

            # Default: AI-generated (INFERRED) assertions run on ingestion
            if source_type == "INFERRED" and trigger_type == "ON_INGESTION":
                logger.debug(
                    f"Assertion {assertion.get('urn')} is INFERRED, "
                    f"defaulting to ON_INGESTION trigger"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking assertion trigger: {e}")
            return False

    def _execute_single_assertion(
        self, assertion: Dict[str, Any], dataset_urn: str
    ) -> None:
        """
        Execute a single SQL assertion and emit results.

        Args:
            assertion: Assertion dictionary from GraphQL
            dataset_urn: URN of the dataset
        """
        assertion_urn = assertion.get("urn")

        try:
            info = assertion.get("info", {})
            assertion_type = info.get("type")

            if assertion_type != "SQL":
                logger.debug(
                    f"Skipping non-SQL assertion {assertion_urn} (type: {assertion_type})"
                )
                return

            sql_assertion = info.get("sqlAssertion")
            if not sql_assertion:
                logger.warning(f"SQL assertion {assertion_urn} has no sqlAssertion field")
                return

            sql_statement = sql_assertion.get("statement")
            operator = sql_assertion.get("operator")
            parameters = sql_assertion.get("parameters", {})

            if not sql_statement:
                logger.warning(f"SQL assertion {assertion_urn} has no SQL statement")
                return

            logger.info(f"Executing SQL assertion {assertion_urn} for {dataset_urn}")

            # Get database connection using connector registry
            try:
                connection = self.connector_registry.get_native_connection(dataset_urn)
            except Exception as e:
                logger.error(
                    f"Failed to get connection for {dataset_urn}: {e}"
                )
                self._emit_assertion_result(
                    assertion_urn, dataset_urn, success=False,
                    error_message=f"Failed to connect: {str(e)}"
                )
                return

            # Execute SQL query
            try:
                result = self._execute_sql(connection, sql_statement)
                logger.debug(f"SQL query returned result: {result}")

                # Evaluate result against assertion parameters
                success, actual_value, error_message = self._evaluate_assertion(
                    result, operator, parameters
                )

                logger.info(
                    f"Assertion {assertion_urn} {'PASSED' if success else 'FAILED'}: "
                    f"actual={actual_value}"
                )

                # Emit assertion result
                if self.config.emit_results:
                    self._emit_assertion_result(
                        assertion_urn, dataset_urn, success,
                        actual_value=actual_value, error_message=error_message
                    )

            except Exception as e:
                logger.error(f"Error executing SQL for assertion {assertion_urn}: {e}")
                self._emit_assertion_result(
                    assertion_urn, dataset_urn, success=False,
                    error_message=f"SQL execution failed: {str(e)}"
                )
            finally:
                try:
                    connection.close()
                except:
                    pass

        except Exception as e:
            logger.error(f"Error executing assertion {assertion_urn}: {e}", exc_info=True)

    def _execute_sql(self, connection: Any, sql: str) -> Any:
        """Execute SQL query and return the result (typically a single value)."""
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        finally:
            cursor.close()

    def _evaluate_assertion(
        self, actual_value: Any, operator: str, parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluate assertion result against expected parameters.

        Returns:
            (success: bool, actual_value_str: str, error_message: str or None)
        """
        try:
            actual_str = str(actual_value) if actual_value is not None else "NULL"

            if operator == "EQUAL_TO":
                expected = parameters.get("value", {}).get("value")
                success = actual_value == float(expected) if expected else False
                error = None if success else f"Expected {expected}, got {actual_str}"
                return success, actual_str, error

            elif operator == "BETWEEN":
                min_val = parameters.get("minValue", {}).get("value")
                max_val = parameters.get("maxValue", {}).get("value")
                success = (
                    float(min_val) <= actual_value <= float(max_val)
                    if min_val and max_val and actual_value is not None
                    else False
                )
                error = None if success else f"Expected between {min_val} and {max_val}, got {actual_str}"
                return success, actual_str, error

            elif operator == "GREATER_THAN":
                threshold = parameters.get("value", {}).get("value")
                success = actual_value > float(threshold) if threshold and actual_value is not None else False
                error = None if success else f"Expected > {threshold}, got {actual_str}"
                return success, actual_str, error

            elif operator == "GREATER_THAN_OR_EQUAL_TO":
                threshold = parameters.get("value", {}).get("value")
                success = actual_value >= float(threshold) if threshold and actual_value is not None else False
                error = None if success else f"Expected >= {threshold}, got {actual_str}"
                return success, actual_str, error

            elif operator == "LESS_THAN":
                threshold = parameters.get("value", {}).get("value")
                success = actual_value < float(threshold) if threshold and actual_value is not None else False
                error = None if success else f"Expected < {threshold}, got {actual_str}"
                return success, actual_str, error

            elif operator == "LESS_THAN_OR_EQUAL_TO":
                threshold = parameters.get("value", {}).get("value")
                success = actual_value <= float(threshold) if threshold and actual_value is not None else False
                error = None if success else f"Expected <= {threshold}, got {actual_str}"
                return success, actual_str, error

            else:
                return False, actual_str, f"Unsupported operator: {operator}"

        except Exception as e:
            return False, str(actual_value), f"Evaluation error: {str(e)}"

    def _emit_assertion_result(
        self,
        assertion_urn: str,
        dataset_urn: str,
        success: bool,
        actual_value: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Emit AssertionRunEvent to DataHub.

        Args:
            assertion_urn: URN of the assertion
            dataset_urn: URN of the dataset
            success: Whether assertion passed
            actual_value: Actual value from SQL query
            error_message: Error message if failed
        """
        try:
            run_event = AssertionRunEventClass(
                timestampMillis=int(datetime.now().timestamp() * 1000),
                assertionUrn=assertion_urn,
                asserteeUrn=dataset_urn,
                runId=f"{assertion_urn}_{int(datetime.now().timestamp())}",
                status=AssertionRunStatusClass.COMPLETE,
                result={
                    "type": "SUCCESS" if success else "FAILURE",
                    "actualAggValue": float(actual_value) if actual_value and actual_value != "NULL" else None,
                    "externalUrl": None,
                    "nativeResults": {
                        "actualValue": actual_value,
                        "success": success,
                        "errorMessage": error_message,
                    } if error_message or actual_value else None,
                },
            )

            mcp = MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=run_event,
            )

            self.ctx.graph.graph.emit(mcp)
            logger.debug(f"Emitted assertion result for {assertion_urn}")

        except Exception as e:
            logger.error(f"Failed to emit assertion result for {assertion_urn}: {e}")

    def close(self) -> None:  # type: ignore[override]
        """Cleanup resources."""
        return
