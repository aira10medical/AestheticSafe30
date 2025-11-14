#!/bin/bash
# ============================================================================
# AestheticSafe - Liberar dominio app.aestheticsafe.com
# ============================================================================
# Propósito: Desvincular dominio de Google Cloud (sin eliminar servicios)
# ADVERTENCIA: Solo ejecutar después de confirmar que el backup está completo
# ============================================================================

echo "⚠️  AestheticSafe - Liberación de Dominio"
echo "======================================================="
echo ""
echo "Este script va a DESVINCULAR app.aestheticsafe.com de Google Cloud"
echo "NO eliminará servicios ni aplicaciones, solo liberará el dominio."
echo ""

# Confirmación de seguridad
read -p "¿Confirmás que el backup fue completado exitosamente? (yes/no): " confirm1
if [ "$confirm1" != "yes" ]; then
    echo "❌ Operación cancelada. Completá el backup primero."
    exit 1
fi

read -p "¿Estás seguro de liberar app.aestheticsafe.com? (yes/no): " confirm2
if [ "$confirm2" != "yes" ]; then
    echo "❌ Operación cancelada por el usuario."
    exit 1
fi

echo ""
echo "🔍 Verificando dominios actuales..."
gcloud app domain-mappings list

echo ""
echo "🔓 Liberando app.aestheticsafe.com..."
gcloud app domain-mappings delete app.aestheticsafe.com --quiet

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ DOMINIO LIBERADO EXITOSAMENTE"
    echo "======================================================="
    echo ""
    echo "📋 Verificaciones post-liberación:"
    echo ""
    
    # Verificar que no esté más en la lista
    echo "1️⃣ Dominios restantes en Google Cloud:"
    gcloud app domain-mappings list
    echo ""
    
    # Verificar DNS (puede tardar en propagarse)
    echo "2️⃣ Verificación DNS (puede mostrar cache):"
    nslookup app.aestheticsafe.com
    echo ""
    
    echo "✅ SIGUIENTE PASO:"
    echo "   1. Esperá ~5 minutos para propagación DNS inicial"
    echo "   2. Ejecutá 3_verify_domain_free.sh para confirmar"
    echo "   3. Una vez libre, configurá el dominio en Replit"
    echo ""
else
    echo ""
    echo "❌ ERROR al liberar el dominio"
    echo "   Verificá que el dominio exista en:"
    gcloud app domain-mappings list
    echo ""
fi
