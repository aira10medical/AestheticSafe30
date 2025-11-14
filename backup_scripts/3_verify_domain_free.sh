#!/bin/bash
# ============================================================================
# AestheticSafe - Verificar que el dominio esté libre
# ============================================================================
# Propósito: Confirmar que app.aestheticsafe.com ya no apunta a Google Cloud
# ============================================================================

echo "🔍 AestheticSafe - Verificación de Dominio Liberado"
echo "======================================================="
echo ""

DOMAIN="app.aestheticsafe.com"

echo "Verificando dominio: $DOMAIN"
echo ""

# Verificar en Google Cloud
echo "1️⃣ Verificando en Google Cloud App Engine..."
if gcloud app domain-mappings list --format="value(id)" | grep -q "^${DOMAIN}$"; then
    echo "   ❌ El dominio AÚN está mapeado en Google Cloud"
    echo "   Ejecutá: gcloud app domain-mappings delete $DOMAIN"
else
    echo "   ✅ El dominio NO está mapeado en Google Cloud"
fi
echo ""

# Verificar DNS actual
echo "2️⃣ Verificando DNS actual (nslookup)..."
nslookup_output=$(nslookup $DOMAIN 2>&1)
echo "$nslookup_output"

if echo "$nslookup_output" | grep -q "NXDOMAIN"; then
    echo "   ✅ NXDOMAIN - Dominio libre (no resuelve a ninguna IP)"
elif echo "$nslookup_output" | grep -q "Address:"; then
    current_ip=$(echo "$nslookup_output" | grep "Address:" | tail -1 | awk '{print $2}')
    echo "   ⚠️  Dominio aún apunta a: $current_ip"
    echo "   Puede ser cache DNS, esperá unos minutos y volvé a verificar"
fi
echo ""

# Verificar DNS con dig (más detallado)
echo "3️⃣ Verificando DNS actual (dig)..."
dig_output=$(dig $DOMAIN +short 2>&1)
if [ -z "$dig_output" ]; then
    echo "   ✅ Sin respuesta DNS - Dominio libre"
else
    echo "   Respuesta DNS actual:"
    dig $DOMAIN
    echo ""
    echo "   ⚠️  Si ves IPs de Google Cloud, esperá propagación DNS"
fi
echo ""

# Resumen
echo "======================================================="
echo "📊 RESUMEN"
echo "======================================================="
echo ""
echo "✅ Podés continuar con Replit si:"
echo "   - Google Cloud no muestra el dominio mapeado"
echo "   - DNS muestra NXDOMAIN o no resuelve"
echo ""
echo "⏳ Esperá propagación DNS si:"
echo "   - Aún ves IPs de Google Cloud"
echo "   - Tiempo de propagación típico: 5 min - 24 horas"
echo ""
echo "🚀 PRÓXIMO PASO (cuando esté libre):"
echo "   1. Ir a Replit → Deployments → Settings"
echo "   2. Click 'Link a domain'"
echo "   3. Ingresar: app.aestheticsafe.com"
echo "   4. Copiar registros DNS (A y TXT) a DonWeb/Cloudflare"
echo ""
