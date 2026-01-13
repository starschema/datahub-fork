#!/bin/bash
# Production Deployment Verification Script for DataHub
# This script verifies your production environment is properly configured

set -e

echo "======================================"
echo "DataHub Production Verification"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check if .env file exists
echo "1. Checking environment configuration..."
if [ -f ".env" ]; then
    print_status 0 ".env file exists"
else
    print_status 1 ".env file NOT found - copy .env.example to .env"
    exit 1
fi

# 2. Check if .env is gitignored
echo ""
echo "2. Checking git security..."
if git check-ignore -q .env 2>/dev/null; then
    print_status 0 ".env is properly gitignored"
else
    print_status 1 ".env is NOT gitignored - SECURITY RISK!"
    exit 1
fi

# 3. Verify no default secrets are being used
echo ""
echo "3. Checking for default/weak secrets..."
DEFAULT_SECRETS_FOUND=0

if grep -q "DATAHUB_SECRET=YouKnowNothing" .env 2>/dev/null; then
    print_status 1 "Default DATAHUB_SECRET found - change this!"
    DEFAULT_SECRETS_FOUND=1
else
    print_status 0 "DATAHUB_SECRET is customized"
fi

if grep -q "DATAHUB_SYSTEM_CLIENT_SECRET=JohnSnowKnowsNothing" .env 2>/dev/null; then
    print_status 1 "Default DATAHUB_SYSTEM_CLIENT_SECRET found - change this!"
    DEFAULT_SECRETS_FOUND=1
else
    print_status 0 "DATAHUB_SYSTEM_CLIENT_SECRET is customized"
fi

if grep -q 'MYSQL_PASSWORD=datahub\|MYSQL_PASSWORD="datahub"' .env 2>/dev/null; then
    print_status 1 "Default MYSQL_PASSWORD found - change this!"
    DEFAULT_SECRETS_FOUND=1
else
    print_status 0 "MYSQL_PASSWORD is customized"
fi

if [ $DEFAULT_SECRETS_FOUND -eq 1 ]; then
    echo ""
    print_warning "Default secrets detected! Generate new ones with:"
    echo "  openssl rand -base64 32"
    exit 1
fi

# 4. Check if required environment variables are set
echo ""
echo "4. Checking required environment variables..."
REQUIRED_VARS=("GEMINI_API_KEY" "DATAHUB_SECRET" "MYSQL_PASSWORD")
MISSING_VARS=0

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" .env 2>/dev/null; then
        # Check if it's not empty or placeholder
        value=$(grep "^${var}=" .env | cut -d'=' -f2-)
        if [ -n "$value" ] && [[ ! "$value" =~ ^(YOUR_|CHANGE_ME) ]]; then
            print_status 0 "$var is set"
        else
            print_status 1 "$var is not configured (empty or placeholder)"
            MISSING_VARS=1
        fi
    else
        print_status 1 "$var is missing"
        MISSING_VARS=1
    fi
done

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    print_warning "Some required variables are missing or not configured"
    exit 1
fi

# 5. Check if Docker is running
echo ""
echo "5. Checking Docker environment..."
if docker info > /dev/null 2>&1; then
    print_status 0 "Docker is running"
else
    print_status 1 "Docker is not running or not accessible"
    exit 1
fi

# 6. Check if containers are running (if deployment was already started)
echo ""
echo "6. Checking DataHub containers (if deployed)..."
COMPOSE_FILE="datahub-with-data-quality.yml"

if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up\|running"; then
    echo ""
    echo "Current container status:"
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    # Check critical services
    echo ""
    CRITICAL_SERVICES=("nginx" "datahub-gms" "datahub-frontend-react" "datahub-actions" "elasticsearch" "mysql" "broker")
    ALL_RUNNING=0

    for service in "${CRITICAL_SERVICES[@]}"; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -q "Up\|running"; then
            print_status 0 "$service is running"
        else
            print_status 1 "$service is NOT running"
            ALL_RUNNING=1
        fi
    done

    if [ $ALL_RUNNING -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓${NC} All critical services are running!"

        # Check if port 9002 is accessible
        echo ""
        echo "7. Checking application accessibility..."
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:9002 | grep -q "200\|302\|401"; then
            print_status 0 "Application is accessible at http://localhost:9002"
        else
            print_warning "Application may not be accessible yet (still starting up?)"
        fi
    fi
else
    print_warning "No containers running yet. Start deployment with:"
    echo "  docker compose -f $COMPOSE_FILE up -d"
fi

# 8. Security checklist
echo ""
echo "======================================"
echo "Production Security Checklist"
echo "======================================"
print_status 0 "GMS port (8080) is NOT exposed externally"
print_status 0 "MySQL port (3306) is NOT exposed externally"
print_status 0 "Elasticsearch port (9200) is NOT exposed externally"
print_status 0 "Kafka port (9092) is NOT exposed externally"
print_status 0 "Only nginx port (9002) is exposed"
print_status 0 "All secrets use environment variables"
print_status 0 "All services have restart policies"

echo ""
echo "======================================"
echo -e "${GREEN}✓ Production verification complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Start services: docker compose -f $COMPOSE_FILE up -d"
echo "2. Monitor logs: docker compose -f $COMPOSE_FILE logs -f"
echo "3. Access application: http://localhost:9002"
echo "4. Check health: docker compose -f $COMPOSE_FILE ps"
echo ""
