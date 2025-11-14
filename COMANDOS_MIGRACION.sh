#!/bin/bash
# ============================================================================
# AestheticSafe - Comandos de Migración (Copy/Paste Ready)
# ============================================================================
# Ejecutar en Google Cloud Shell
# Objetivo: Liberar app.aestheticsafe.com SIN borrar V1
# ============================================================================

echo "🔍 AestheticSafe - Migración de Dominio"
echo "========================================"
echo ""

# ============================================================================
# PASO 1: Verificar proyecto actual
# ============================================================================
echo "1️⃣ Proyecto actual de Google Cloud:"
gcloud config get-value project
echo ""

# ============================================================================
# PASO 2: Ver dominios mapeados actualmente
# ============================================================================
echo "2️⃣ Dominios mapeados actualmente:"
gcloud app domain-mappings list
echo ""
echo "⚠️  Vamos a LIBERAR app.aestheticsafe.com (sin borrar servicios)"
echo ""

# ============================================================================
# PASO 3: Liberar el dominio (COPY/PASTE este bloque)
# ============================================================================
read -p "¿Continuar con la liberación del dominio? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
    echo ""
    echo "🔓 Liberando app.aestheticsafe.com..."
    gcloud app domain-mappings delete app.aestheticsafe.com --quiet
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ DOMINIO LIBERADO EXITOSAMENTE"
        echo ""
        echo "3️⃣ Verificando que el dominio fue liberado:"
        gcloud app domain-mappings list
        echo ""
        echo "4️⃣ Verificando DNS (puede mostrar cache):"
        nslookup app.aestheticsafe.com
        echo ""
        echo "✅ PRÓXIMOS PASOS:"
        echo "   1. Esperá ~10-30 min para propagación DNS inicial"
        echo "   2. En Replit → Deployments → Settings → Link domain"
        echo "   3. Agregá: app.aestheticsafe.com"
        echo "   4. Copiá los registros DNS (A y TXT) a DonWeb/Cloudflare"
        echo "   5. Esperá propagación DNS completa (1-2 horas típico)"
        echo "   6. Verificá: https://app.aestheticsafe.com"
        echo ""
        echo "⚠️  V1 sigue activa en Google Cloud (solo liberamos el dominio)"
        echo "   NO se borró ningún servicio - todo queda como backup"
        echo ""
    else
        echo ""
        echo "❌ ERROR al liberar el dominio"
        echo "   Verificá que el dominio exista:"
        gcloud app domain-mappings list
    fi
else
    echo "❌ Operación cancelada"
fi
