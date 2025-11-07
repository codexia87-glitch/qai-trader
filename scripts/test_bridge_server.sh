#!/bin/bash
#
# Script para probar el Bridge Server desde Mac
#

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Bridge Server - Test Script${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Configuración
HOST=${1:-0.0.0.0}
PORT=${2:-8443}
TOKEN=${QAI_TOKEN:-'w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo'}

BASE_URL="http://${HOST}:${PORT}"

echo "Testeando: $BASE_URL"
echo ""

# Test 1: Health check (sin auth)
echo -e "${YELLOW}Test 1: Health Check (sin autenticación)${NC}"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Health check OK${NC}"
    echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 2: Next signal con token
echo -e "${YELLOW}Test 2: Get Next Signal (con token)${NC}"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" \
    -H "X-QAI-Token: $TOKEN" \
    "$BASE_URL/next")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Request successful${NC}"
    echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Request failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 3: Next signal sin token (debe fallar)
echo -e "${YELLOW}Test 3: Get Next Signal (sin token - debe fallar)${NC}"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" \
    "$BASE_URL/next")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Correctamente rechazado (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Debería haber fallado (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 4: Verificar puerto listening
echo -e "${YELLOW}Test 4: Verificar puerto $PORT${NC}"
if lsof -nP -iTCP:$PORT -sTCP:LISTEN > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Puerto $PORT está en LISTEN${NC}"
    lsof -nP -iTCP:$PORT -sTCP:LISTEN
else
    echo -e "${RED}✗ Puerto $PORT NO está en LISTEN${NC}"
fi
echo ""

# Obtener IP local para instrucciones
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Tests completados${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Para probar desde Windows (PowerShell):"
echo ""
echo "\$TOKEN=\"$TOKEN\""
echo "Invoke-WebRequest -Uri \"http://$LOCAL_IP:$PORT/health\""
echo "Invoke-WebRequest -Uri \"http://$LOCAL_IP:$PORT/next\" -Headers @{ \"X-QAI-Token\"=\$TOKEN }"
echo ""
