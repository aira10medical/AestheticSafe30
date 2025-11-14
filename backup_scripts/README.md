# 🔧 AestheticSafe - Scripts de Migración a Replit

**Objetivo**: Liberar `app.aestheticsafe.com` de Google Cloud para apuntarlo a AestheticSafe V3 en Replit.

---

## 📋 Flujo de Migración

```
Google Cloud               Replit
┌─────────────┐           ┌─────────────┐
│ V1/V2       │           │ V3 (nuevo)  │
│ (actual)    │  ──────>  │ PHI redact  │
└─────────────┘           │ PDF v3.1    │
      ↓                   │ TLS activo  │
 Backup + Release         └─────────────┘
                                 ↓
                          app.aestheticsafe.com
```

---

## 🚀 Pasos de Ejecución

### **Pre-requisitos**

1. Abrí **Google Cloud Shell** (https://console.cloud.google.com)
2. Seleccioná el proyecto correcto:
   ```bash
   gcloud config set project [TU_PROJECT_ID]
   ```
3. Descargá estos scripts a Cloud Shell

---

### **Paso 1: Backup de Configuración** ✅

Ejecutá el primer script para exportar toda la configuración actual:

```bash
chmod +x 1_export_gcloud_config.sh
./1_export_gcloud_config.sh
```

**Qué hace:**
- ✅ Exporta configuración de App Engine
- ✅ Exporta servicios de Cloud Run
- ✅ Lista buckets de Cloud Storage
- ✅ Exporta dominios mapeados
- ✅ Exporta IAM policies
- ✅ Verifica DNS actual

**Resultado:** Directorio `aestheticsafe_backup_YYYYMMDD_HHMMSS/` con todos los YAMLs.

---

### **Paso 2: Liberar Dominio** 🔓

Una vez confirmado el backup, liberá el dominio:

```bash
chmod +x 2_release_domain.sh
./2_release_domain.sh
```

**Qué hace:**
- ⚠️ Solicita confirmación doble
- 🔓 Ejecuta `gcloud app domain-mappings delete app.aestheticsafe.com`
- ✅ Verifica que el dominio fue removido

**Importante:** Esto **NO elimina** la aplicación, solo libera el dominio.

---

### **Paso 3: Verificar Dominio Libre** 🔍

Esperá ~5 minutos y verificá que el dominio esté libre:

```bash
chmod +x 3_verify_domain_free.sh
./3_verify_domain_free.sh
```

**Qué verifica:**
- ✅ Dominio no aparece en `gcloud app domain-mappings list`
- ✅ DNS muestra NXDOMAIN o sin respuesta
- ⏳ Si aún muestra IP de Google, esperá propagación DNS (hasta 24h)

---

### **Paso 4: Configurar en Replit** 🚀

Una vez que el dominio esté libre:

1. **En Replit:**
   - Ir a **Deployments** → **Settings**
   - Click **"Link a domain"**
   - Ingresar: `app.aestheticsafe.com`
   - Copiar los registros DNS (A y TXT)

2. **En DonWeb/Cloudflare:**
   - Agregar los registros A y TXT que Replit proporcionó
   - Ejemplo:
     ```
     Type: A
     Name: app
     Value: [IP de Replit]
     
     Type: TXT
     Name: _replit-challenge.app
     Value: [código de verificación]
     ```

3. **Esperar propagación:**
   - Tiempo típico: 1-24 horas
   - Verificar en Replit que muestre "Verified"

4. **Probar:**
   - Abrir `https://app.aestheticsafe.com`
   - Verificar splash screen, PDF, email

---

### **Paso 5 (OPCIONAL): Limpieza de Google Cloud** 🗑️

**⚠️ SOLO ejecutar después de confirmar que V3 funciona perfectamente en producción.**

```bash
chmod +x 4_optional_cleanup.sh
./4_optional_cleanup.sh
```

**Qué hace:**
- 🗑️ Elimina servicios de Cloud Run
- 🗑️ Intenta eliminar servicios de App Engine
- ⚠️ **IRREVERSIBLE** - solo para ahorro de costos

---

## 📦 Archivos de Backup Generados

Después del Paso 1, vas a tener:

```
aestheticsafe_backup_YYYYMMDD_HHMMSS/
├── project_config.yaml              # Config general del proyecto
├── backup_app_engine_config.yaml    # Config App Engine
├── backup_app_engine_services.yaml  # Servicios App Engine
├── backup_domain_mappings.yaml      # Dominios mapeados
├── backup_cloudrun_services.yaml    # Listado Cloud Run
├── backup_cloudrun_[service].yaml   # Config de cada servicio
├── backup_storage_buckets.txt       # Listado de buckets
├── backup_iam_policy.yaml           # IAM policies
├── backup_dns_verification.txt      # DNS actual
└── ...
```

**Guardá estos archivos** en un lugar seguro por si necesitás rollback.

---

## ⚠️ Troubleshooting

### "Domain not found" al ejecutar paso 2
- El dominio puede estar en otro proyecto de GCP
- Verificá con: `gcloud projects list`
- Cambiá de proyecto: `gcloud config set project [PROJECT_ID]`

### DNS aún muestra IP de Google después de liberar
- **Normal**: Propagación DNS puede tardar hasta 24 horas
- Cache local: probá `nslookup app.aestheticsafe.com 8.8.8.8`
- Podés configurar Replit igual, va a funcionar cuando propague

### Replit no verifica el dominio
- Verificá que los registros DNS estén correctos (A y TXT)
- Esperá propagación completa
- Verificá con: `dig app.aestheticsafe.com +short`

---

## 🎯 Resultado Final

- ✅ **V1/V2**: Backups completos en Google Cloud Shell
- ✅ **Dominio**: `app.aestheticsafe.com` libre y apuntando a Replit
- ✅ **V3**: Funcionando en producción con PHI redaction
- ✅ **V2 Demo**: Mantiene `app.aestheticsafe.com.ar` como demo

---

## 📞 Contacto

Si encontrás algún problema durante la migración, contactá a soporte técnico con los archivos de backup generados.

**Backup location:** `aestheticsafe_backup_[timestamp]/`
