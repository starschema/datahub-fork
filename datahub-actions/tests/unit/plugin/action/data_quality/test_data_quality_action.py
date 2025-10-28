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

from unittest.mock import MagicMock, Mock

import pytest

from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetFieldProfileClass,
    DatasetProfileClass,
    EntityChangeEventClass,
)
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.data_quality.action import DataQualityAction


@pytest.fixture
def mock_graph():
    """Create mock DataHub graph client."""
    graph = Mock()
    graph.emit_mcp = Mock()
    return graph


@pytest.fixture
def pipeline_context_with_graph(mock_graph):
    """Create pipeline context with mocked graph."""
    return PipelineContext(pipeline_name="test", graph=mock_graph)


@pytest.fixture
def dataset_change_event():
    """Create dataset change event for testing."""
    return EntityChangeEvent.from_class(
        EntityChangeEventClass(
            "dataset",
            "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)",
            "MODIFY",
            "UPDATE",
            AuditStampClass(0, "urn:li:corpuser:datahub"),
            0,
            None,
            None,
        )
    )


@pytest.fixture
def dataset_profile():
    """Create sample dataset profile."""
    return DatasetProfileClass(
        timestampMillis=1000000,
        rowCount=1000,
        columnCount=5,
        fieldProfiles=[
            DatasetFieldProfileClass(
                fieldPath="age",
                uniqueCount=50,
                nullCount=10,
            )
        ],
    )


def test_create_action():
    """Test action can be created with valid config."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "row_count_check",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:*",
                "params": {"min_rows": "1"},
            }
        ],
    }

    ctx = PipelineContext(pipeline_name="test", graph=Mock())
    action = DataQualityAction.create(config, ctx)

    assert action is not None
    assert action.config.enabled is True
    assert len(action.config.tests) == 1


def test_create_action_requires_graph():
    """Test action creation fails without graph."""
    config = {"enabled": True, "tests": []}
    ctx = PipelineContext(pipeline_name="test", graph=None)

    with pytest.raises(ValueError, match="DataHub graph client is required"):
        DataQualityAction.create(config, ctx)


def test_action_skips_when_disabled(pipeline_context_with_graph, dataset_change_event):
    """Test action does nothing when disabled."""
    config = {"enabled": False, "tests": []}
    action = DataQualityAction.create(config, pipeline_context_with_graph)

    event_env = EventEnvelope("EntityChangeEvent_v1", dataset_change_event, {})
    action.act(event_env)

    pipeline_context_with_graph.graph.emit_mcp.assert_not_called()


def test_action_skips_non_dataset_events(pipeline_context_with_graph):
    """Test action ignores non-dataset entities."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "test1",
                "type": "table_row_count",
                "dataset_pattern": "*",
                "params": {"min_rows": "1"},
            }
        ],
    }
    action = DataQualityAction.create(config, pipeline_context_with_graph)

    # Create non-dataset event
    non_dataset_event = EntityChangeEvent.from_class(
        EntityChangeEventClass(
            "dashboard",
            "urn:li:dashboard:(looker,1)",
            "MODIFY",
            "UPDATE",
            AuditStampClass(0, "urn:li:corpuser:datahub"),
            0,
            None,
            None,
        )
    )

    event_env = EventEnvelope("EntityChangeEvent_v1", non_dataset_event, {})
    action.act(event_env)

    pipeline_context_with_graph.graph.emit_mcp.assert_not_called()


def test_action_processes_profile_based_test(
    pipeline_context_with_graph, dataset_change_event, dataset_profile
):
    """Test action executes profile-based test and emits assertions."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "row_count_check",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:*",
                "params": {"min_rows": "1", "max_rows": "10000"},
            }
        ],
    }

    # Mock profile retrieval
    pipeline_context_with_graph.graph.get_aspect = Mock(return_value=dataset_profile)

    action = DataQualityAction.create(config, pipeline_context_with_graph)

    event_env = EventEnvelope("EntityChangeEvent_v1", dataset_change_event, {})
    action.act(event_env)

    # Verify profile was retrieved
    pipeline_context_with_graph.graph.get_aspect.assert_called_once()

    # Verify assertions were emitted (should be 2: info + result)
    assert pipeline_context_with_graph.graph.emit_mcp.call_count == 2


def test_action_handles_missing_profile(
    pipeline_context_with_graph, dataset_change_event
):
    """Test action handles missing profile gracefully."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "row_count_check",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:*",
                "params": {"min_rows": "1"},
            }
        ],
    }

    # Mock profile as missing
    pipeline_context_with_graph.graph.get_aspect = Mock(return_value=None)

    action = DataQualityAction.create(config, pipeline_context_with_graph)

    event_env = EventEnvelope("EntityChangeEvent_v1", dataset_change_event, {})

    # Should not raise exception
    action.act(event_env)

    # Should still emit assertions (test fails, but assertion is recorded)
    assert pipeline_context_with_graph.graph.emit_mcp.call_count == 2


def test_action_filters_by_dataset_pattern(pipeline_context_with_graph, dataset_profile):
    """Test action only runs tests matching dataset pattern."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "postgres_test",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:(urn:li:dataPlatform:postgres,*)",
                "params": {"min_rows": "1"},
            },
            {
                "name": "mysql_test",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:(urn:li:dataPlatform:mysql,*)",
                "params": {"min_rows": "1"},
            },
        ],
    }

    pipeline_context_with_graph.graph.get_aspect = Mock(return_value=dataset_profile)
    action = DataQualityAction.create(config, pipeline_context_with_graph)

    # MySQL dataset event
    mysql_event = EntityChangeEvent.from_class(
        EntityChangeEventClass(
            "dataset",
            "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)",
            "MODIFY",
            "UPDATE",
            AuditStampClass(0, "urn:li:corpuser:datahub"),
            0,
            None,
            None,
        )
    )

    event_env = EventEnvelope("EntityChangeEvent_v1", mysql_event, {})
    action.act(event_env)

    # Should only emit assertions for mysql_test (2 MCPs: info + result)
    assert pipeline_context_with_graph.graph.emit_mcp.call_count == 2


def test_close_action(pipeline_context_with_graph):
    """Test action can be closed without errors."""
    config = {"enabled": True, "tests": []}
    action = DataQualityAction.create(config, pipeline_context_with_graph)

    action.close()


def test_test_registry_completeness():
    """Test that all expected test types are registered."""
    from datahub_actions.plugin.action.data_quality.test_executor import TEST_REGISTRY

    # Profile-based table tests
    assert "table_row_count" in TEST_REGISTRY
    assert "table_row_count_equals" in TEST_REGISTRY
    assert "table_column_count_equals" in TEST_REGISTRY
    assert "table_column_count_between" in TEST_REGISTRY

    # Profile-based column tests
    assert "column_values_not_null" in TEST_REGISTRY
    assert "column_values_unique" in TEST_REGISTRY
    assert "column_min_between" in TEST_REGISTRY
    assert "column_max_between" in TEST_REGISTRY
    assert "column_mean_between" in TEST_REGISTRY
    assert "column_median_between" in TEST_REGISTRY
    assert "column_stddev_between" in TEST_REGISTRY
    assert "column_distinct_count_between" in TEST_REGISTRY
    assert "column_unique_proportion_between" in TEST_REGISTRY
    assert "column_null_count_equals" in TEST_REGISTRY

    # Query-based column tests
    assert "column_value_range" in TEST_REGISTRY
    assert "column_values_in_set" in TEST_REGISTRY
    assert "column_values_not_in_set" in TEST_REGISTRY
    assert "column_values_match_regex" in TEST_REGISTRY
    assert "column_values_not_match_regex" in TEST_REGISTRY
    assert "column_length_between" in TEST_REGISTRY

    # Query-based table tests
    assert "table_custom_sql" in TEST_REGISTRY

    # Total: 21 tests (14 profile-based + 7 query-based)
    assert len(TEST_REGISTRY) == 21


def test_unknown_test_type_returns_empty(pipeline_context_with_graph, dataset_change_event, dataset_profile):
    """Test that unknown test type is handled gracefully."""
    config = {
        "enabled": True,
        "tests": [
            {
                "name": "unknown_test",
                "type": "nonexistent_test_type",
                "dataset_pattern": "urn:li:dataset:*",
                "params": {},
            }
        ],
    }

    pipeline_context_with_graph.graph.get_aspect = Mock(return_value=dataset_profile)
    action = DataQualityAction.create(config, pipeline_context_with_graph)

    event_env = EventEnvelope("EntityChangeEvent_v1", dataset_change_event, {})
    action.act(event_env)

    # Should not emit any assertions for unknown test type
    pipeline_context_with_graph.graph.emit_mcp.assert_not_called()
