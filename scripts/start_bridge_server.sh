#!/bin/bash
#
# Script para lanzar el Bridge Server en Mac
# Uso: ./start_bridge_server.sh
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}QAI Bridge Server - Startup${NC}"
echo -e "${GREEN}================================${NC}"

# Directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Verificar que existe el módulo bridge_server
if [ ! -f "core/bridge_server.py" ]; then
    echo -e "${RED}ERROR: No se encuentra core/bridge_server.py${NC}"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p logs

# Verificar credenciales
if [ -z "$QAI_TOKEN" ]; then
    echo -e "${YELLOW}WARNING: QAI_TOKEN no está configurado${NC}"
    echo "Usando token por defecto..."
    export QAI_TOKEN='w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo'
fi

if [ -z "$QAI_HMAC_SECRET" ]; then
    echo -e "${YELLOW}WARNING: QAI_HMAC_SECRET no está configurado${NC}"
    echo "Usando secret por defecto..."
    export QAI_HMAC_SECRET='D2urWwuvEeShrcK5T1EUSu_H6eSHotC16Vq9FdCz3BaOAYeQ_SuAq1gGV7xYCZYKl-Ld1YVdShATwBjZk2BiQg'
fi

# Puerto
PORT=${BRIDGE_PORT:-8443}

# Verificar si el puerto está en uso
if lsof -nP -iTCP:$PORT -sTCP:LISTEN > /dev/null 2>&1; then
    echo -e "${RED}ERROR: El puerto $PORT ya está en uso${NC}"
    echo "Procesos usando el puerto:"
    lsof -nP -iTCP:$PORT -sTCP:LISTEN
    echo ""
    echo "Para matar el proceso:"
    echo "  PID=\$(lsof -nP -t -iTCP:$PORT -sTCP:LISTEN) ; [ -n \"\$PID\" ] && kill \$PID"
    exit 1
fi

# Verificar Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}ERROR: Python no está instalado${NC}"
    exit 1
fi

# Verificar dependencias
echo "Verificando dependencias..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Instalando FastAPI...${NC}"
    pip install fastapi uvicorn python-dotenv
fi

# Obtener IP local
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

echo ""
echo -e "${GREEN}Configuración:${NC}"
echo "  Puerto: $PORT"
echo "  IP Local: $LOCAL_IP"
echo "  Token configurado: ${QAI_TOKEN:0:20}..."
echo "  HMAC configurado: ${QAI_HMAC_SECRET:0:20}..."
echo "  Log file: logs/bridge_server.out"
echo ""

# Preguntar si ejecutar en background
read -p "¿Ejecutar en background? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Lanzando en background..."
    nohup env QAI_TOKEN="$QAI_TOKEN" QAI_HMAC_SECRET="$QAI_HMAC_SECRET" \
        python -m uvicorn core.bridge_server:app \
        --host 0.0.0.0 \
        --port $PORT \
        --log-level info \
        > logs/bridge_server.out 2>&1 &
    
    PID=$!
    echo -e "${GREEN}Bridge server lanzado con PID: $PID${NC}"
    echo ""
    sleep 2
    
    # Verificar que está corriendo
    if lsof -nP -iTCP:$PORT -sTCP:LISTEN > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server está corriendo en puerto $PORT${NC}"
        echo ""
        echo "Para verificar:"
        echo "  curl http://0.0.0.0:$PORT/health"
        echo "  curl http://$LOCAL_IP:$PORT/health"
        echo ""
        echo "Desde Windows (PowerShell):"
        echo "  \$TOKEN=\"$QAI_TOKEN\""
        echo "  Invoke-WebRequest -Uri \"http://$LOCAL_IP:$PORT/health\" -Headers @{ \"X-QAI-Token\"=\$TOKEN }"
        echo ""
        echo "Para ver logs:"
        echo "  tail -f logs/bridge_server.out"
        echo ""
        echo "Para detener:"
        echo "  kill $PID"
    else
        echo -e "${RED}✗ Server no está corriendo${NC}"
        echo "Ver logs en: logs/bridge_server.out"
    fi
else
    echo "Lanzando en foreground (Ctrl+C para detener)..."
    env QAI_TOKEN="$QAI_TOKEN" QAI_HMAC_SECRET="$QAI_HMAC_SECRET" \
        python -m uvicorn core.bridge_server:app \
        --host 0.0.0.0 \
        --port $PORT \
        --log-level info
fi
