# QAI Bridge Server - Guía de Configuración Completa

## 🎯 Objetivo

Tener un bridge FastAPI en tu Mac escuchando en la red local (LAN) y una EA en Windows/MT5 que:
- Lee órdenes desde `/next`
- Ejecuta en MT5
- (Opcional) envía feedback a `/feedback`

Todo en **tiempo real**, sin simuladores, usando tu cola de señales real.

---

## 📋 Arquitectura

### Mac (Bridge Server - FastAPI/Uvicorn)
- **Puerto**: `8443`
- **Host**: `0.0.0.0` (accesible desde LAN)
- **Autenticación**:
  - **Token-only** para IPs en whitelist LAN (ej: `192.168.0.0/24`)
  - **HMAC** para otros orígenes

### Windows (EA MT5)
- **Conecta a**: `http://IP-MAC:8443` (ej: `http://192.168.0.100:8443`)
- **Autenticación**: Solo header `X-QAI-Token` (si está en whitelist LAN)

---

## 🚀 Paso 1: Configurar el Bridge Server en Mac

### 1.1 Verificar credenciales

```bash
# Estas son las credenciales por defecto
export QAI_TOKEN='w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo'
export QAI_HMAC_SECRET='D2urWwuvEeShrcK5T1EUSu_H6eSHotC16Vq9FdCz3BaOAYeQ_SuAq1gGV7xYCZYKl-Ld1YVdShATwBjZk2BiQg'
```

### 1.2 Matar proceso anterior (si existe)

```bash
PID=$(lsof -nP -t -iTCP:8443 -sTCP:LISTEN)
[ -n "$PID" ] && kill "$PID"
```

### 1.3 Instalar dependencias

```bash
pip install fastapi uvicorn python-dotenv
```

### 1.4 Lanzar el servidor

**Opción A: Usando el script (recomendado)**
```bash
cd /Users/soybillonario/Visual\ studio\ Code\ insiders/qai-trader
./scripts/start_bridge_server.sh
```

**Opción B: Manual**
```bash
cd /Users/soybillonario/Visual\ studio\ Code\ insiders/qai-trader

# En background
nohup env QAI_TOKEN="$QAI_TOKEN" QAI_HMAC_SECRET="$QAI_HMAC_SECRET" \
  python -m uvicorn core.bridge_server:app \
  --host 0.0.0.0 \
  --port 8443 \
  --log-level info \
  > logs/bridge_server.out 2>&1 &

# En foreground (para debugging)
env QAI_TOKEN="$QAI_TOKEN" QAI_HMAC_SECRET="$QAI_HMAC_SECRET" \
  python -m uvicorn core.bridge_server:app \
  --host 0.0.0.0 \
  --port 8443 \
  --log-level info
```

### 1.5 Verificar que está corriendo

```bash
# Ver proceso
lsof -nP -iTCP:8443 -sTCP:LISTEN

# Test health check
curl http://0.0.0.0:8443/health

# Ver logs
tail -f logs/bridge_server.out
```

### 1.6 Obtener tu IP local

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1
```

Ejemplo de resultado: `192.168.0.100` (usa esta IP en la EA de Windows)

---

## 🪟 Paso 2: Configurar la EA en Windows/MT5

### 2.1 Copiar el archivo de la EA

Copia `mt5/QAI_Bridge_Client.mq5` a:
```
C:\Users\TuUsuario\AppData\Roaming\MetaQuotes\Terminal\XXXXXXXXXXXX\MQL5\Experts\
```

### 2.2 Compilar la EA en MetaEditor

1. Abre MetaEditor (F4 desde MT5)
2. Abre `QAI_Bridge_Client.mq5`
3. Compila (F7)
4. Verifica que no hay errores

### 2.3 Configurar URL permitidas en MT5

**IMPORTANTE**: MT5 bloquea WebRequest por defecto.

1. Herramientas → Opciones → Expert Advisors
2. En "WebRequest URL permitidas", añade:
   ```
   http://192.168.0.100:8443
   ```
   (Reemplaza `192.168.0.100` con tu IP Mac)

3. **Marca las opciones**:
   - ✅ Permitir WebRequest para las URL listadas
   - ✅ Permitir trading automático

### 2.4 Configurar parámetros de la EA

En MT5, arrastra `QAI_Bridge_Client` a un gráfico. Configura:

- **BridgeHost**: `192.168.0.100` (tu IP Mac)
- **BridgePort**: `8443`
- **QAI_Token**: `w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo`
- **PollIntervalSeconds**: `5` (cada 5 segundos busca señales)
- **EnableFeedback**: `true`

### 2.5 Activar la EA

1. Presiona "OK" para aplicar la EA al gráfico
2. En la pestaña "Expertos" verás:
   ```
   [QAI-Bridge] Initializing...
   [QAI-Bridge] Bridge URL: http://192.168.0.100:8443
   [QAI-Bridge] Successfully connected to bridge server
   ```

---

## 🧪 Paso 3: Probar el Sistema

### 3.1 Test desde Mac

```bash
./scripts/test_bridge_server.sh
```

Esto probará:
- ✅ Health check
- ✅ Autenticación con token
- ✅ Rechazo sin token

### 3.2 Test desde Windows (PowerShell)

```powershell
# Configurar variables
$HOST_MAC = "192.168.0.100"
$TOKEN = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"

# Test 1: Health check
Invoke-WebRequest -Uri "http://${HOST_MAC}:8443/health"

# Test 2: Get next signal (con autenticación)
Invoke-WebRequest -Uri "http://${HOST_MAC}:8443/next" `
    -Headers @{ "X-QAI-Token"=$TOKEN } `
    -Method GET
```

**Resultado esperado**: 
- HTTP 200 con `{"status":"empty"}` si no hay señales
- HTTP 200 con `{"status":"ok","signal":{...}}` si hay señales

### 3.3 Generar una señal de prueba

En Mac:

```bash
python scripts/emit_example_signal.py
```

Esto creará un archivo `.sig.json` en `example_signals/`.

**En 5 segundos**, la EA en Windows:
1. Detectará la señal
2. La ejecutará en MT5
3. Moverá el archivo a `example_signals/archived/`
4. Enviará feedback al bridge

---

## 🔍 Troubleshooting

### ❌ Error: `invalid_token`

**Causa**: El token en la EA no coincide con el del servidor.

**Solución**:
```bash
# En Mac, verifica:
echo $QAI_TOKEN

# En Windows/EA, verifica que el parámetro QAI_Token sea EXACTAMENTE el mismo
```

### ❌ Error: `WebRequest error 4060`

**Causa**: URL no está en la whitelist de MT5.

**Solución**:
1. Herramientas → Opciones → Expert Advisors
2. Añade: `http://TU_IP_MAC:8443`
3. Marca "Permitir WebRequest para las URL listadas"
4. Reinicia MT5

### ❌ Error: Bridge no responde

**Diagnóstico**:
```bash
# ¿Está corriendo?
lsof -nP -iTCP:8443 -sTCP:LISTEN

# ¿Responde local?
curl http://0.0.0.0:8443/health

# ¿Responde en LAN?
curl http://$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1):8443/health

# Ver logs
tail -f logs/bridge_server.out
```

**Soluciones**:
- Firewall: Asegúrate que el puerto 8443 esté abierto
- IP cambiada: Verifica tu IP con `ifconfig`
- Proceso muerto: Relanza con `./scripts/start_bridge_server.sh`

### ❌ Error: `timestamp_replay_or_drift`

**Causa**: Reloj desincronizado o timestamp reutilizado.

**Solución**:
- Si usas HMAC (no LAN), cada request necesita un timestamp NUEVO
- Sincroniza el reloj: `sudo sntp -sS time.apple.com` (Mac)

### ❌ IP dinámica (router cambia la IP)

**Solución**: El bridge ya está configurado con whitelist por SUBRED:
```python
TOKEN_ONLY_NETS = [
    "192.168.0.0/24",   # Acepta 192.168.0.1-254
    "192.168.1.0/24",   # Acepta 192.168.1.1-254
]
```

Así, si tu Mac cambia de `.100` a `.105`, seguirá funcionando.

---

## 📊 Estructura de Señales

### JSON Format (`.sig.json`)

```json
{
  "version": "1",
  "id": "abc123",
  "symbol": "EURUSD",
  "side": "BUY",
  "volume": 0.1,
  "price": null,
  "sl_pts": 50,
  "tp_pts": 100,
  "ts": "2025-11-06T12:00:00Z"
}
```

### Text Format (`.sig`)

```
symbol=EURUSD
side=BUY
volume=0.1
price=
sl_pts=50
tp_pts=100
ts=2025-11-06T12:00:00Z
```

---

## 🔐 Configuración de Seguridad

### Token-Only (LAN)

Para clientes en la LAN (`192.168.0.0/24`):
- Solo requiere header `X-QAI-Token`
- No requiere HMAC
- Más rápido y simple

### HMAC (Internet)

Para clientes fuera de LAN:
- Requiere headers:
  - `X-QAI-Token`: tu token
  - `X-QAI-TS`: timestamp Unix (segundos)
  - `X-QAI-Sig`: HMAC-SHA256(secret, token|ts|body)

**Ejemplo de firma HMAC**:
```python
import hmac
import hashlib
import time

token = "tu_token"
secret = "tu_secret"
timestamp = str(int(time.time()))
body = b""  # Para GET requests

message = f"{token}|{timestamp}|".encode() + body
signature = hmac.new(
    secret.encode(),
    message,
    hashlib.sha256
).hexdigest()
```

---

## 📁 Archivos Clave

```
qai-trader/
├── core/
│   └── bridge_server.py          # FastAPI bridge server
├── mt5/
│   ├── QAI_Bridge_Client.mq5     # EA para MT5 (Windows)
│   └── qai_bridge.mq5            # EA antigua (no usar)
├── scripts/
│   ├── start_bridge_server.sh    # Lanzar bridge (Mac)
│   ├── test_bridge_server.sh     # Probar bridge (Mac)
│   └── emit_example_signal.py    # Generar señal de prueba
├── example_signals/              # Cola de señales
│   ├── *.sig.json                # Señales pendientes
│   └── archived/                 # Señales procesadas
└── logs/
    └── bridge_server.out         # Logs del servidor
```

---

## 🎯 Checklist Final

### En Mac:
- [ ] Bridge corriendo en `0.0.0.0:8443`
- [ ] `curl http://0.0.0.0:8443/health` → 200 OK
- [ ] `lsof -nP -iTCP:8443 -sTCP:LISTEN` → proceso Python
- [ ] IP local conocida (ej: `192.168.0.100`)

### En Windows:
- [ ] EA compilada sin errores
- [ ] URL en whitelist de MT5: `http://IP-MAC:8443`
- [ ] Parámetro `BridgeHost` = IP Mac
- [ ] Parámetro `QAI_Token` = mismo token del servidor
- [ ] EA activa en gráfico
- [ ] Logs muestran: "Successfully connected to bridge server"

### Test End-to-End:
- [ ] Generar señal: `python scripts/emit_example_signal.py`
- [ ] En 5-10 segundos, EA ejecuta la orden en MT5
- [ ] Archivo movido a `example_signals/archived/`
- [ ] Logs de la EA muestran: "Order executed successfully"

---

## 🆘 Soporte

Si algo falla:

1. **Ver logs del bridge**:
   ```bash
   tail -f logs/bridge_server.out
   ```

2. **Ver logs de la EA**:
   En MT5 → Pestaña "Expertos" (busca `[QAI-Bridge]`)

3. **Verificar conectividad**:
   ```powershell
   # Desde Windows
   Test-NetConnection -ComputerName 192.168.0.100 -Port 8443
   ```

4. **Probar manualmente**:
   ```powershell
   $TOKEN = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"
   Invoke-WebRequest -Uri "http://192.168.0.100:8443/next" `
       -Headers @{ "X-QAI-Token"=$TOKEN } `
       -Method GET
   ```

---

## 🎉 ¡Todo Listo!

Si completaste todos los pasos, ahora tienes:
- ✅ Bridge en Mac escuchando en LAN
- ✅ EA en Windows conectada al bridge
- ✅ Pipeline completo: señal → cola → bridge → EA → MT5
- ✅ Feedback de ejecución enviado al bridge

**Siguiente paso**: Integrar tu generador de señales real para que escriba a `example_signals/`.
