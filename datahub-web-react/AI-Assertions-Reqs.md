AI Assertion Generator — Final Architecture & Requirements (fits DataHub “Quality”)
Placement in UI

Where: Dataset → Quality (renamed)

Existing subtabs: Summary | Assertions | Data Contract

Add: AI Assistant (4th subtab)

Path:
datahub-web-react/src/app/entity/shared/tabs/Dataset/Validations/[somwhere in here]

It must read the current dataset URN from route context and never ask the user for it.

What the tab does (four phases)

Validate (feasibility)

Fetch columns & types (and nullable, key flags if available) for the current dataset only.

Input: NL rule. Output: { feasible, reasons[], schema }.

Reject on schema mismatch or logical flaws (e.g., avg() on STRING).

Generate

Compose strict prompt → LLM → read-only SQL + structured assertion config.

Execute (preview)

Run via DataHub Actions connector for this dataset (read-only role), with limits (timeout, row limit).

Return pass/fail + metrics; no raw samples by default.

Persist

Write a DataHub Assertion scoped to this dataset URN and flagged ai_generated=true.

This assertion is now part of this dataset’s Quality and will auto-run on every ingestion (existing Actions runtime).

Scoping & “runs on ingestion”

Scope: Persisted assertion must reference the current dataset URN (single-entity scope), not a pattern.

Run policy: Use the existing DataHub Data Quality (Actions) execution path. Persisted assertions are discovered and executed on each ingestion cycle automatically—no special scheduler required.

Coexistence: This lives in addition to baseline/profile-derived assertions. It should appear under:

Quality → Assertions (standard list)

With properties.ai_generated = true and properties.creator = <principal>

Data sources for validation

Schema & types: Resolve from GMS Graph/GraphQL for the dataset URN: column names, types, nullability, primary keys, and (if present) profiler stats (min/max, distincts).

SLA/contract context: Optionally read Data Contract subtab aspects to enforce constraints (e.g., non-null columns, min freshness).

Contracts (backend API)

Backend service: ai-assertion-builder (FastAPI). All JSON.

POST /validate
Req { datasetUrn, nlRule }
Res { feasible:boolean, reasons?:string[], schema:{cols:[{name,type,nullable}]} }

POST /generate
Req { datasetUrn, nlRule }
Res { sql:string, config:{type:string, params:any}, guardrails:{readonly:true, limits:{rowLimit:number, timeoutSec:number}} }

POST /execute
Req { datasetUrn, sql, config }
Res { passed:boolean, metrics:{rowCount?:number, aggregates?:any} }

POST /persist
Req { datasetUrn, sql, config, metadata?:{title?, description?, tags?[]} }
Res { assertionUrn:string }

GET /healthz → {status:"ok"}

Error codes: SCHEMA_MISMATCH, POLICY_DENIED, GENERATION_FAILED, CONNECTOR_NOT_FOUND, EXECUTION_TIMEOUT, PERSIST_FAILED.

LLM usage (Gemini-first, configurable)

Provider & models (env):

LLM_PROVIDER=gemini

GEMINI_API_KEY (required if provider=gemini)

GEMINI_MODEL one of:

gemini-2.0-flash (fast, cheap; default)

gemini-2.0-pro (higher quality)

Also support: OPENAI_API_KEY + OPENAI_MODEL, AZURE_OPENAI_* via config switch.

System prompt guardrails: must output only read-only SELECT/CTE SQL, fully-qualified names, no DDL/DML, inject time window and LIMIT.

Static validators: AST parse, forbid joins across datasets unless lineage allowed, enforce timeout & LIMIT.

Persistence model (no schema break)

Use Assertion entity with enriched properties:

properties.ai_generated = true

properties.persistent = true

properties.sqlHash = sha256(sql)

customProperties = { nlRule, guardrails, createdWith: "AI Assistant v1" }

Scope to the dataset URN so it shows under this dataset only and runs on ingestion.

Execution (must use DataHub connector)

Resolve connector via existing Actions connector registry using dataset URN.

Execute with read-only credentials; default limits: timeoutSec=8, rowLimit=1000.

Engines supported by your deployment (e.g., Snowflake, Postgres, BigQuery, Databricks) via adapters.

Frontend notes

File: AIAssistantTab.tsx alongside Quality subtabs.

Components: RuleInput, PhasePanel, SqlPreview, MetricsCard.

State machine: idle → validating → generating → executing → ready_to_persist → persisted.

Pull schema immediately on mount (for the current dataset URN) so validation is instant.

Show granular errors with retry.

Compose & images (Windows-friendly; local build)
services:
  datahub-frontend-react:
    build:
      context: ./datahub-web-react        # adjust to your actual path
      dockerfile: Dockerfile
    image: custom-datahub-frontend-react:latest
    # … existing env/ports/depends_on …

  ai-assertion-builder:
    build:
      context: ./datahub-actions          # FastAPI service location
      dockerfile: Dockerfile
    image: my-datahub-actions:latest
    environment:
      LLM_PROVIDER: ${LLM_PROVIDER:-gemini}
      GEMINI_API_KEY: ${GEMINI_API_KEY:?}
      GEMINI_MODEL: ${GEMINI_MODEL:-gemini-2.0-flash}
      # optional alternates:
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_MODEL: ${OPENAI_MODEL:-}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT:-}
      AZURE_OPENAI_KEY: ${AZURE_OPENAI_KEY:-}
    ports:
      - "8082:8082"
    depends_on:
      - datahub-actions


Windows tips:
PowerShell before up:
$env:HOME = $env:USERPROFILE
Ensure H:\ drive is shared in Docker Desktop.
Bring up: docker compose -f datahub-with-data-quality.yml up -d --build

Security & governance

RBAC: Only users with “Manage Assertions” on this dataset can execute/persist.

No secrets to the browser; all DSNs/keys are server-side.

Audit log: {ts, user, datasetUrn, phase, requestId, sqlHash, result, durationMs}.

PII safety: Preview returns aggregates/metrics; samples gated and redacted by policy.

Acceptance criteria

New AI Assistant subtab visible under Quality for a dataset.

Typing a rule triggers Validate → Generate → Execute → Persist with clear status.

Validation uses actual columns & types from this dataset.

Persisted assertion appears under Quality → Assertions for this dataset, with ai_generated=true.

Assertion auto-runs on ingestion via Actions connector, no extra wiring.

Compose builds frontend locally (no registry pull) and AI builder service responds on :8082.

“Do this, not that”

✅ Use existing Actions connector for all execution; do not DIY connections.

✅ Scope assertions to this dataset URN only; no global patterns.

✅ Default to gemini-2.0-flash; allow model override via env.

❌ No DDL/DML; ❌ No secrets in client; ❌ No force-pushes on shared branches.