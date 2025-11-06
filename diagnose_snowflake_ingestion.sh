#!/bin/bash
# Diagnostic script for Snowflake ingestion debugging
# Run this on your Digital Ocean server

echo "======================================================================="
echo "DataHub Snowflake Ingestion Diagnostic Tool"
echo "======================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find containers
echo -e "${YELLOW}[1/7] Finding DataHub containers...${NC}"
GMS_CONTAINER=$(docker ps --filter "name=datahub-gms" --format "{{.ID}}" | head -n 1)
ACTIONS_CONTAINER=$(docker ps --filter "name=datahub-actions" --format "{{.ID}}" | head -n 1)

if [ -z "$GMS_CONTAINER" ]; then
    echo -e "${RED}✗ datahub-gms container not found!${NC}"
    exit 1
fi

if [ -z "$ACTIONS_CONTAINER" ]; then
    echo -e "${RED}✗ datahub-actions container not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found GMS container: $GMS_CONTAINER${NC}"
echo -e "${GREEN}✓ Found Actions container: $ACTIONS_CONTAINER${NC}"
echo ""

# Check Snowflake connectivity
echo -e "${YELLOW}[2/7] Testing Snowflake connectivity from Actions container...${NC}"
echo "Testing DNS resolution for STARSCHEMA-STARSCHEMA.snowflakecomputing.com..."
docker exec $ACTIONS_CONTAINER nslookup STARSCHEMA-STARSCHEMA.snowflakecomputing.com 2>&1 | head -10

echo ""
echo "Testing HTTPS connectivity to Snowflake..."
docker exec $ACTIONS_CONTAINER curl -v --max-time 10 https://STARSCHEMA-STARSCHEMA.snowflakecomputing.com 2>&1 | head -20
echo ""

# Check environment variables
echo -e "${YELLOW}[3/7] Checking Snowflake credentials environment variable...${NC}"
ENV_CHECK=$(docker exec $ACTIONS_CONTAINER printenv | grep -i snowflake || echo "NOT_FOUND")
if [ "$ENV_CHECK" = "NOT_FOUND" ]; then
    echo -e "${RED}✗ No Snowflake-related environment variables found${NC}"
else
    echo -e "${GREEN}✓ Found Snowflake environment variables (showing keys only):${NC}"
    docker exec $ACTIONS_CONTAINER printenv | grep -i snowflake | cut -d'=' -f1
fi
echo ""

# Check recent ingestion execution requests
echo -e "${YELLOW}[4/7] Checking recent ingestion execution requests...${NC}"
docker logs $ACTIONS_CONTAINER 2>&1 | grep -E "Received execution request|RUN_INGEST|Processing execution request" | tail -10
echo ""

# Check for Snowflake ingestion errors
echo -e "${YELLOW}[5/7] Searching for Snowflake-related errors in Actions container...${NC}"
SNOWFLAKE_ERRORS=$(docker logs $ACTIONS_CONTAINER 2>&1 | grep -iE "snowflake.*error|snowflake.*failed|connection.*refused|timeout.*snowflake" | tail -20)
if [ -z "$SNOWFLAKE_ERRORS" ]; then
    echo -e "${GREEN}✓ No obvious Snowflake errors found${NC}"
else
    echo -e "${RED}Found Snowflake-related errors:${NC}"
    echo "$SNOWFLAKE_ERRORS"
fi
echo ""

# Check GMS logs for ingestion errors
echo -e "${YELLOW}[6/7] Checking GMS container for ingestion-related errors...${NC}"
GMS_ERRORS=$(docker logs $GMS_CONTAINER 2>&1 | grep -iE "ingestion.*error|executionrequest.*error" | tail -10)
if [ -z "$GMS_ERRORS" ]; then
    echo -e "${GREEN}✓ No ingestion errors in GMS logs${NC}"
else
    echo -e "${RED}Found ingestion errors in GMS:${NC}"
    echo "$GMS_ERRORS"
fi
echo ""

# Show recent completed/failed execution requests
echo -e "${YELLOW}[7/7] Checking execution request results...${NC}"
docker logs $ACTIONS_CONTAINER 2>&1 | grep -E "Execution.*completed|Execution.*failed|SubProcessIngestionTask" | tail -15
echo ""

# Network policy recommendations
echo "======================================================================="
echo -e "${YELLOW}RECOMMENDATIONS:${NC}"
echo "======================================================================="
echo ""
echo "1. If DNS resolution fails:"
echo "   - Check if your Digital Ocean droplet can resolve external DNS"
echo "   - Verify DNS settings in docker-compose.yml"
echo ""
echo "2. If connection times out or is refused:"
echo "   - Most likely: Snowflake Network Policy blocking Digital Ocean IP"
echo "   - Get your server's public IP: curl ifconfig.me"
echo "   - Add it to Snowflake network policy allowlist"
echo ""
echo "3. If credentials are not found:"
echo "   - Check environment variable 'datahub_snowflake' is set"
echo "   - Verify it's passed to the Actions container in docker-compose"
echo ""
echo "4. To get full ingestion run logs:"
echo "   docker logs $ACTIONS_CONTAINER 2>&1 | grep -A 50 'RUN_INGEST'"
echo ""
echo "5. To monitor real-time ingestion:"
echo "   docker logs -f $ACTIONS_CONTAINER"
echo ""
echo "======================================================================="
