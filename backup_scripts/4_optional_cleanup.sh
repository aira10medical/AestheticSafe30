#!/bin/bash
# ============================================================================
# AestheticSafe - Limpieza opcional de recursos Google Cloud
# ============================================================================
# ADVERTENCIA: SOLO ejecutar después de confirmar que V3 funciona en Replit
# Este script ELIMINA servicios de Google Cloud
# ============================================================================

echo "⚠️⚠️⚠️ ADVERTENCIA - ELIMINACIÓN DE RECURSOS ⚠️⚠️⚠️"
echo "======================================================="
echo ""
echo "Este script va a ELIMINAR recursos de Google Cloud:"
echo "  - Servicios de Cloud Run"
echo "  - Servicios de App Engine"
echo ""
echo "SOLO ejecutá esto si:"
echo "  ✅ V3 está funcionando perfectamente en Replit"
echo "  ✅ app.aestheticsafe.com está conectado a Replit"
echo "  ✅ Confirmaste que no necesitás rollback a V1/V2"
echo ""

read -p "¿Confirmás que V3 funciona OK en producción? (yes/no): " confirm1
if [ "$confirm1" != "yes" ]; then
    echo "❌ Operación cancelada."
    exit 1
fi

read -p "¿REALMENTE querés ELIMINAR los servicios de Google Cloud? (yes/no): " confirm2
if [ "$confirm2" != "yes" ]; then
    echo "❌ Operación cancelada por el usuario."
    exit 1
fi

echo ""
echo "🗑️  Procediendo con limpieza..."
echo ""

# Listar servicios Cloud Run
echo "1️⃣ Servicios Cloud Run a eliminar:"
gcloud run services list
echo ""

read -p "¿Eliminar TODOS los servicios Cloud Run? (yes/no): " confirm_run
if [ "$confirm_run" = "yes" ]; then
    for service in $(gcloud run services list --format="value(name)"); do
        echo "   🗑️  Eliminando: $service"
        gcloud run services delete "$service" --quiet --region=$(gcloud run services describe "$service" --format="value(region)" 2>/dev/null | head -1)
    done
fi

# Listar servicios App Engine
echo ""
echo "2️⃣ Servicios App Engine:"
gcloud app services list
echo ""

read -p "¿Eliminar servicio 'default' de App Engine? (yes/no): " confirm_app
if [ "$confirm_app" = "yes" ]; then
    echo "   ⚠️  No se puede eliminar el servicio 'default' sin eliminar toda la app"
    echo "   Si querés eliminar App Engine completo, ejecutá:"
    echo "   gcloud projects delete [PROJECT_ID]  # (NO RECOMENDADO)"
    echo ""
    echo "   Alternativa: Dejar el servicio pero sin dominio asignado (ya hecho)"
fi

echo ""
echo "✅ LIMPIEZA COMPLETADA"
echo "======================================================="
echo ""
echo "📊 Recursos restantes:"
gcloud app services list 2>/dev/null || echo "  Sin App Engine activo"
gcloud run services list 2>/dev/null || echo "  Sin Cloud Run activo"
echo ""
