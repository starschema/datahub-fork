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

import pytest
from unittest.mock import MagicMock, patch

from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry


class TestConnectorRegistry:
    """Unit tests for ConnectorRegistry."""

    @pytest.fixture
    def connector_configs(self):
        """Sample connector configurations."""
        return {
            "mysql": {
                "connection_string": "mysql://user:pass@localhost:3306/testdb"
            },
            "postgres": {
                "connection_string": "postgresql://user:pass@localhost:5432/testdb"
            },
            "snowflake": {
                "connection_string": "snowflake://user:pass@account/db/schema"
            },
        }

    @pytest.fixture
    def registry(self, connector_configs):
        """Create a ConnectorRegistry with sample configs."""
        return ConnectorRegistry(connector_configs)

    def test_init_empty(self):
        """Test initialization with no configs."""
        registry = ConnectorRegistry()
        assert registry.connector_configs == {}
        assert registry._engines == {}

    def test_init_with_configs(self, connector_configs):
        """Test initialization with connector configs."""
        registry = ConnectorRegistry(connector_configs)
        assert registry.connector_configs == connector_configs
        assert registry._engines == {}

    def test_register_connector(self):
        """Test registering a new connector."""
        registry = ConnectorRegistry()
        registry.register_connector("mysql", "mysql://user:pass@localhost/db")

        assert "mysql" in registry.connector_configs
        assert registry.connector_configs["mysql"]["connection_string"] == "mysql://user:pass@localhost/db"

    def test_register_connector_overwrites_existing(self, registry):
        """Test that registering a connector overwrites existing config."""
        new_conn_str = "mysql://newuser:newpass@newhost:3307/newdb"
        registry.register_connector("mysql", new_conn_str)

        assert registry.connector_configs["mysql"]["connection_string"] == new_conn_str

    def test_register_connector_clears_cached_engine(self, registry):
        """Test that registering a connector clears cached engine."""
        # Simulate a cached engine
        mock_engine = MagicMock()
        registry._engines["mysql"] = mock_engine

        # Register new connector for mysql
        registry.register_connector("mysql", "mysql://new:connection@localhost/db")

        # Cached engine should be cleared
        assert "mysql" not in registry._engines

    def test_extract_platform_from_urn_mysql(self):
        """Test extracting platform from MySQL dataset URN."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"
        platform = ConnectorRegistry._extract_platform_from_urn(urn)
        assert platform == "mysql"

    def test_extract_platform_from_urn_postgres(self):
        """Test extracting platform from PostgreSQL dataset URN."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,public.orders,PROD)"
        platform = ConnectorRegistry._extract_platform_from_urn(urn)
        assert platform == "postgres"

    def test_extract_platform_from_urn_snowflake(self):
        """Test extracting platform from Snowflake dataset URN."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD)"
        platform = ConnectorRegistry._extract_platform_from_urn(urn)
        assert platform == "snowflake"

    def test_extract_platform_from_urn_invalid_format(self):
        """Test extracting platform from invalid URN returns None."""
        urn = "invalid-urn-format"
        platform = ConnectorRegistry._extract_platform_from_urn(urn)
        assert platform is None

    def test_extract_platform_from_urn_no_platform(self):
        """Test extracting platform from URN without dataPlatform returns None."""
        urn = "urn:li:dataset:(some,other,format)"
        platform = ConnectorRegistry._extract_platform_from_urn(urn)
        assert platform is None

    def test_get_connection_string_success(self, registry):
        """Test getting connection string for registered platform."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"
        conn_str = registry.get_connection_string(urn)
        assert conn_str == "mysql://user:pass@localhost:3306/testdb"

    def test_get_connection_string_platform_not_registered(self, registry):
        """Test getting connection string for unregistered platform returns None."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:oracle,schema.table,PROD)"
        conn_str = registry.get_connection_string(urn)
        assert conn_str is None

    def test_get_connection_string_invalid_urn(self, registry):
        """Test getting connection string for invalid URN returns None."""
        urn = "invalid-urn"
        conn_str = registry.get_connection_string(urn)
        assert conn_str is None

    def test_has_connector_true(self, registry):
        """Test has_connector returns True for registered platform."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,public.users,PROD)"
        assert registry.has_connector(urn) is True

    def test_has_connector_false(self, registry):
        """Test has_connector returns False for unregistered platform."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:oracle,schema.table,PROD)"
        assert registry.has_connector(urn) is False

    def test_has_connector_invalid_urn(self, registry):
        """Test has_connector returns False for invalid URN."""
        urn = "invalid-urn"
        assert registry.has_connector(urn) is False

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_with_explicit_connection_string(self, mock_create_engine):
        """Test get_engine with explicitly provided connection string."""
        registry = ConnectorRegistry()
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        conn_str = "mysql://user:pass@localhost/db"
        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)"

        engine = registry.get_engine(urn, connection_string=conn_str)

        assert engine == mock_engine
        mock_create_engine.assert_called_once_with(conn_str)

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_from_registry(self, mock_create_engine, registry):
        """Test get_engine looks up connection string from registry."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"
        engine = registry.get_engine(urn)

        assert engine == mock_engine
        mock_create_engine.assert_called_once_with("mysql://user:pass@localhost:3306/testdb")

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_caches_engine(self, mock_create_engine, registry):
        """Test that get_engine caches engines per platform."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"

        # First call should create engine
        engine1 = registry.get_engine(urn)
        assert engine1 == mock_engine
        assert mock_create_engine.call_count == 1

        # Second call should use cached engine
        engine2 = registry.get_engine(urn)
        assert engine2 == mock_engine
        assert mock_create_engine.call_count == 1  # Should not create again

        # Verify engine is cached
        assert "mysql" in registry._engines
        assert registry._engines["mysql"] == mock_engine

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_platform_not_found(self, mock_create_engine, registry):
        """Test get_engine returns None when platform not registered."""
        urn = "urn:li:dataset:(urn:li:dataPlatform:oracle,schema.table,PROD)"
        engine = registry.get_engine(urn)

        assert engine is None
        mock_create_engine.assert_not_called()

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_invalid_urn(self, mock_create_engine, registry):
        """Test get_engine returns None for invalid URN."""
        urn = "invalid-urn"
        engine = registry.get_engine(urn)

        assert engine is None
        mock_create_engine.assert_not_called()

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_creation_fails(self, mock_create_engine, registry):
        """Test get_engine returns None when engine creation fails."""
        mock_create_engine.side_effect = Exception("Connection failed")

        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"
        engine = registry.get_engine(urn)

        assert engine is None

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_get_engine_explicit_connection_fails(self, mock_create_engine):
        """Test get_engine returns None when explicit connection string fails."""
        mock_create_engine.side_effect = Exception("Invalid connection string")

        registry = ConnectorRegistry()
        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,db.table,PROD)"
        engine = registry.get_engine(urn, connection_string="invalid://conn")

        assert engine is None

    def test_close_all_no_engines(self, registry):
        """Test close_all with no cached engines."""
        # Should not raise any errors
        registry.close_all()
        assert registry._engines == {}

    def test_close_all_with_engines(self, registry):
        """Test close_all disposes all cached engines."""
        # Create mock engines
        mock_engine1 = MagicMock()
        mock_engine2 = MagicMock()

        registry._engines = {
            "mysql": mock_engine1,
            "postgres": mock_engine2,
        }

        registry.close_all()

        # All engines should be disposed
        mock_engine1.dispose.assert_called_once()
        mock_engine2.dispose.assert_called_once()

        # Cache should be cleared
        assert registry._engines == {}

    def test_close_all_handles_errors(self, registry):
        """Test close_all continues even if one engine disposal fails."""
        mock_engine1 = MagicMock()
        mock_engine2 = MagicMock()

        # First engine disposal fails
        mock_engine1.dispose.side_effect = Exception("Disposal failed")

        registry._engines = {
            "mysql": mock_engine1,
            "postgres": mock_engine2,
        }

        # Should not raise exception
        registry.close_all()

        # Both dispose should be attempted
        mock_engine1.dispose.assert_called_once()
        mock_engine2.dispose.assert_called_once()

        # Cache should still be cleared
        assert registry._engines == {}

    def test_context_manager_enter(self, connector_configs):
        """Test context manager __enter__ returns self."""
        with ConnectorRegistry(connector_configs) as registry:
            assert isinstance(registry, ConnectorRegistry)
            assert registry.connector_configs == connector_configs

    def test_context_manager_exit(self, connector_configs):
        """Test context manager __exit__ closes all connections."""
        mock_engine = MagicMock()

        with ConnectorRegistry(connector_configs) as registry:
            registry._engines["mysql"] = mock_engine

        # After exiting context, engines should be disposed
        mock_engine.dispose.assert_called_once()

    @patch("datahub_actions.plugin.action.data_quality.connector_registry.create_engine")
    def test_context_manager_full_workflow(self, mock_create_engine, connector_configs):
        """Test full workflow using context manager."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,mydb.users,PROD)"

        with ConnectorRegistry(connector_configs) as registry:
            # Get engine should work
            engine = registry.get_engine(urn)
            assert engine == mock_engine

        # After exiting, engine should be disposed
        mock_engine.dispose.assert_called_once()
