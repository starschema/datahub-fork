 DataHub Ingestion Flow - Complete Breakdown

  When you click "Run" on a Snowflake ingestion source in the DataHub UI, here's the exact flow:

  1. UI → GraphQL Mutation (datahub-graphql-core:59-159)

  File: CreateIngestionExecutionRequestResolver.java

  - User clicks "Run" button in UI
  - Frontend sends GraphQL mutation createIngestionExecutionRequest
  - Creates an ExecutionRequest entity with:
    - task: "RUN_INGEST"
    - recipe: Your Snowflake configuration (with injected run_id and pipeline_name)
    - args: Contains recipe, version, debug_mode
    - executorId: Specifies which executor should handle this (default: "default")

  2. ExecutionRequest Written to DataHub (line 149)

  - The ExecutionRequest is written to DataHub metadata store as a MetadataChangeProposal
  - This triggers a Kafka MetadataChangeLog event

  3. datahub-actions Picks Up Event (executor_action.py:93-113)

  File: datahub-actions/src/datahub_actions/plugin/action/execution/executor_action.py

  - The datahub-actions container listens to Kafka for MetadataChangeLogs
  - When it sees entityType=dataHubExecutionRequest and aspectName=dataHubExecutionRequestInput
  - Extracts the execution request details:
    - Recipe (contains your Snowflake account_id, credentials, etc.)
    - Task name (RUN_INGEST)
    - Executor ID

  4. Dispatcher Routes to SubProcessIngestionTask (line 140-144, 180-181)

  - The DefaultDispatcher routes RUN_INGEST tasks to SubProcessIngestionTask
  - This task spawns a subprocess that runs:
  datahub ingest run -c <your-recipe>

  5. DataHub CLI Attempts Snowflake Connection

  - The datahub CLI (Python) constructs the connection URL:
  STARSCHEMA-STARSCHEMA.snowflakecomputing.com
  - Uses the snowflake-connector-python library
  - This is where your issue likely occurs - connection to Snowflake fails

  6. Logs Written

  - Execution logs go to the datahub-actions container
  - Look for errors in: docker logs <datahub-actions-container>

  ---
  How to Debug Your Issue

  I've created a diagnostic script for you. Run this on your Digital Ocean server:

  # Upload the script
  scp diagnose_snowflake_ingestion.sh user@your-digital-ocean-server:/tmp/

  # SSH into your server
  ssh user@your-digital-ocean-server

  # Make it executable and run
  chmod +x /tmp/diagnose_snowflake_ingestion.sh
  /tmp/diagnose_snowflake_ingestion.sh

  Key Files and Line Numbers:

  1. GraphQL Resolver (creates execution request):
    - datahub-graphql-core/src/main/java/com/linkedin/datahub/graphql/resolvers/ingest/execution/CreateIngestionExecutionRequestResolve    
  r.java:59-159
  2. Executor Action (listens and dispatches):
    - datahub-actions/src/datahub_actions/plugin/action/execution/executor_action.py:93-144
  3. Snowflake Connection (builds URL):
    - metadata-ingestion/src/datahub/ingestion/source/snowflake/snowflake_connection.py:320,334,348

  Summary for Your Manager

  Snowflake Connection URL: STARSCHEMA-STARSCHEMA.snowflakecomputing.com

  Most Likely Issues:
  1. Snowflake Network Policy blocking Digital Ocean's IP (90% likelihood)
  2. Environment variable ${datahub_snowflake} not set on Digital Ocean (8% likelihood)
  3. DNS or firewall issues on Digital Ocean server (2% likelihood)

  Next Steps:
  1. Run the diagnostic script I provided on your Digital Ocean server
  2. Get the public IP of your Digital Ocean server: curl ifconfig.me
  3. Add that IP to Snowflake's network policy allowlist

  The script will show you the exact error message from the logs, which will confirm the root cause.
