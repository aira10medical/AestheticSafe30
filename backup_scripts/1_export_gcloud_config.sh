#!/bin/bash
# ============================================================================
# AestheticSafe - Backup de configuración Google Cloud
# ============================================================================
# Propósito: Exportar configuración completa antes de liberar app.aestheticsafe.com
# Fecha: 2025-11-04
# Versión: 1.0
# ============================================================================

echo "🔍 AestheticSafe - Backup de Google Cloud Configuration"
echo "======================================================="
echo ""

# Crear directorio de backups
BACKUP_DIR="aestheticsafe_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

echo "📁 Directorio de backup: $BACKUP_DIR"
echo ""

# 1. Configuración general del proyecto
echo "1️⃣ Exportando configuración del proyecto..."
gcloud config list --format yaml > project_config.yaml
gcloud projects describe $(gcloud config get-value project) --format yaml > project_details.yaml

# 2. App Engine (si existe)
echo "2️⃣ Verificando App Engine..."
if gcloud app describe &>/dev/null; then
    echo "   ✅ App Engine encontrada - exportando configuración..."
    gcloud app describe --format yaml > backup_app_engine_config.yaml
    gcloud app services list --format yaml > backup_app_engine_services.yaml
    gcloud app versions list --format yaml > backup_app_engine_versions.yaml
    gcloud app domain-mappings list --format yaml > backup_domain_mappings.yaml
else
    echo "   ℹ️  No se encontró App Engine"
fi

# 3. Cloud Run (si existe)
echo "3️⃣ Verificando Cloud Run..."
if gcloud run services list --format="value(name)" | grep -q .; then
    echo "   ✅ Servicios Cloud Run encontrados - exportando..."
    gcloud run services list --format yaml > backup_cloudrun_services.yaml
    
    # Exportar cada servicio individualmente
    for service in $(gcloud run services list --format="value(name)"); do
        echo "   📦 Exportando servicio: $service"
        gcloud run services describe "$service" --format yaml > "backup_cloudrun_${service}.yaml"
    done
else
    echo "   ℹ️  No se encontraron servicios Cloud Run"
fi

# 4. Cloud Storage (buckets)
echo "4️⃣ Verificando Cloud Storage buckets..."
if gsutil ls | grep -q .; then
    echo "   ✅ Buckets encontrados - listando..."
    gsutil ls -L > backup_storage_buckets.txt
    
    # Listar archivos en cada bucket (sin descargarlos aún)
    for bucket in $(gsutil ls); do
        bucket_name=$(basename "$bucket")
        echo "   📦 Listando contenido de: $bucket_name"
        gsutil ls -r "$bucket" > "backup_bucket_${bucket_name}_contents.txt" 2>/dev/null || true
    done
else
    echo "   ℹ️  No se encontraron buckets"
fi

# 5. Dominios actuales
echo "5️⃣ Verificando dominios mapeados..."
if gcloud app domain-mappings list --format="value(id)" | grep -q .; then
    echo "   ✅ Dominios encontrados:"
    gcloud app domain-mappings list --format="table(id,resourceRecords.flatten())"
    gcloud app domain-mappings list --format yaml > backup_domains_detailed.yaml
else
    echo "   ℹ️  No se encontraron dominios mapeados"
fi

# 6. IAM y Service Accounts
echo "6️⃣ Exportando IAM policies..."
gcloud projects get-iam-policy $(gcloud config get-value project) --format yaml > backup_iam_policy.yaml
gcloud iam service-accounts list --format yaml > backup_service_accounts.yaml

# 7. Networking
echo "7️⃣ Exportando configuración de red..."
gcloud compute addresses list --format yaml > backup_static_ips.yaml 2>/dev/null || echo "   ℹ️  No se encontraron IPs estáticas"

# 8. Verificación de dominios actuales (DNS)
echo "8️⃣ Verificando DNS actual de app.aestheticsafe.com..."
echo "   DNS Lookup:" > backup_dns_verification.txt
nslookup app.aestheticsafe.com >> backup_dns_verification.txt 2>&1 || true
dig app.aestheticsafe.com >> backup_dns_verification.txt 2>&1 || true

echo ""
echo "✅ BACKUP COMPLETADO"
echo "======================================================="
echo "📂 Archivos generados en: $BACKUP_DIR"
echo ""
ls -lh
echo ""
echo "⚠️  PRÓXIMO PASO:"
echo "   Revisar los archivos generados y ejecutar 2_release_domain.sh"
echo "   para liberar app.aestheticsafe.com"
echo ""
