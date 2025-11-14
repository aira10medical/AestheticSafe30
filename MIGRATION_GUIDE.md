# 🚀 AestheticSafe V3 - Guía de Migración a Producción

**Fecha**: 2024-11-04  
**Versión**: 3.1  
**Objetivo**: Migrar de Google Cloud (V1/V2) a Replit (V3) en `app.aestheticsafe.com`

---

## 📊 Estado Actual

| Versión | Ubicación | Dominio | Status |
|---------|-----------|---------|--------|
| **V1** | Google Cloud (App Engine/Cloud Run) | `app.aestheticsafe.com` | 🔴 A reemplazar |
| **V2** | Replit/Cloud | `app.aestheticsafe.com.ar` | 🟢 Mantener como demo |
| **V3** | Replit (listo) | - | 🟡 Listo para deployment |

---

## ✅ Checklist Pre-Migración

Antes de empezar, confirmá que:

- [ ] AestheticSafe V3 está funcionando correctamente en Replit
- [ ] Audit score: 28/29 checks PASSED (96.5%)
- [ ] PHI redaction integrado y funcionando
- [ ] PDF v3.1 con horizontal colored bars funcionando
- [ ] Google Sheets logging activo (V3_Calculadora_Evaluaciones, etc.)
- [ ] SendGrid email delivery configurado
- [ ] TLS/HTTPS activo en Replit
- [ ] Tenés acceso a Google Cloud Console
- [ ] Tenés acceso a DNS provider (DonWeb/Cloudflare)

---

## 🔧 Proceso de Migración

### **Fase 1: Backup (Google Cloud Shell)** ⏱️ 10 minutos

1. Abrí [Google Cloud Shell](https://console.cloud.google.com)

2. Descargá y ejecutá el script de backup:
   ```bash
   # Desde este repo Replit, copiá backup_scripts/ a Cloud Shell
   cd backup_scripts
   chmod +x 1_export_gcloud_config.sh
   ./1_export_gcloud_config.sh
   ```

3. Verificá que se generaron los archivos:
   ```bash
   ls -lh aestheticsafe_backup_*/
   ```

4. **CRÍTICO**: Descargá el directorio de backup a tu máquina local:
   ```bash
   # En Cloud Shell, click los 3 puntos → Download file
   # O usar: gcloud storage cp -r aestheticsafe_backup_* gs://[tu-bucket]/
   ```

---

### **Fase 2: Liberar Dominio** ⏱️ 5 minutos

1. Ejecutá el script de liberación:
   ```bash
   chmod +x 2_release_domain.sh
   ./2_release_domain.sh
   ```

2. Confirmá las dos preguntas de seguridad (escribí `yes`)

3. Verificá que el comando completó exitosamente:
   ```
   ✅ DOMINIO LIBERADO EXITOSAMENTE
   ```

---

### **Fase 3: Verificar Propagación DNS** ⏱️ 5-30 minutos

1. Esperá ~5 minutos iniciales

2. Ejecutá verificación:
   ```bash
   chmod +x 3_verify_domain_free.sh
   ./3_verify_domain_free.sh
   ```

3. **Escenarios posibles:**

   - ✅ **NXDOMAIN o sin respuesta**: Dominio libre → continuar a Fase 4
   - ⏳ **Aún muestra IP de Google**: Esperá y volvé a verificar en 10 min
   - ⚠️ **Error**: El dominio no fue liberado → repetir Fase 2

---

### **Fase 4: Configurar Replit** ⏱️ 10 minutos

1. **En Replit:**
   - Ir a tu proyecto AestheticSafe
   - Click **"Publish"** (si aún no deployed)
   - Seleccionar **"Autoscale"**
   - Ir a **Deployments** → **Settings** → **Domains**

2. **Link custom domain:**
   - Click **"Link a domain"**
   - Ingresar: `app.aestheticsafe.com`
   - Click **"Next"**

3. **Copiar registros DNS:**
   - Replit va a mostrar 2 registros:
     ```
     Type: A
     Name: app (o @)
     Value: [IP de Replit, ej: 35.190.X.X]
     
     Type: TXT
     Name: _replit-challenge.app
     Value: [código largo]
     ```

---

### **Fase 5: Configurar DNS Provider** ⏱️ 10 minutos

**En DonWeb / Cloudflare:**

1. Ir a DNS Management para `aestheticsafe.com`

2. **Agregar/Modificar registro A:**
   ```
   Type: A
   Name: app
   Value: [IP copiada de Replit]
   TTL: 300 (5 min) o Auto
   Proxy: Desactivado (si usás Cloudflare)
   ```

3. **Agregar registro TXT:**
   ```
   Type: TXT
   Name: _replit-challenge.app
   Value: [código copiado de Replit]
   TTL: 300 o Auto
   ```

4. **Guardar cambios**

---

### **Fase 6: Esperar Propagación** ⏱️ 1-24 horas

1. **Monitorear en Replit:**
   - Volver a Deployments → Settings → Domains
   - Esperar que muestre: ✅ **"Verified"**
   - Tiempo típico: 10 minutos - 2 horas
   - Máximo: 24 horas

2. **Verificar manualmente:**
   ```bash
   # En tu terminal local
   nslookup app.aestheticsafe.com 8.8.8.8
   # Debe mostrar la IP de Replit
   
   dig app.aestheticsafe.com +short
   # Debe mostrar la IP de Replit
   ```

3. **Cuando esté verificado:**
   - Abrir: `https://app.aestheticsafe.com`
   - Debe cargar AestheticSafe V3
   - SSL/TLS debe estar activo automáticamente

---

### **Fase 7: Testing en Producción** ⏱️ 30 minutos

**Test Checklist:**

- [ ] Splash screen aparece correctamente (pure white, 0.19em spacing)
- [ ] Multi-idioma funciona (ES/EN/PT/FR)
- [ ] Formulario de evaluación completo funciona
- [ ] PDF v3.1 se genera con horizontal colored bars
- [ ] Email delivery funciona (SendGrid)
- [ ] Google Sheets logging funciona (V3_Calculadora_Evaluaciones)
- [ ] PHI redaction activo en logs (emails masked: `j***e@e****e.com`)
- [ ] Emoji feedback funciona (😞 😐 🙂)
- [ ] Mobile responsive funciona
- [ ] HTTPS/TLS activo (candado en navegador)

**Verificar logs en Replit:**
```bash
# En la consola de Replit, verificar que emails estén masked
[SAFE_LOG] Email send result {'email': 'j***e@e****e.com', 'status': 202, 'ok': True}
```

---

### **Fase 8: Rollback Plan (si algo falla)** 🔙

**Si V3 no funciona correctamente:**

1. **Opción A - Volver a Google Cloud:**
   ```bash
   # En Google Cloud Shell
   gcloud app domain-mappings create app.aestheticsafe.com --certificate-id=[TU_CERT]
   ```

2. **Opción B - Usar V2 temporalmente:**
   - Cambiar DNS de `app.aestheticsafe.com` para apuntar a `app.aestheticsafe.com.ar`
   - Esto da tiempo para debuggear V3

3. **Restaurar desde backup:**
   - Usar archivos en `aestheticsafe_backup_YYYYMMDD_HHMMSS/`
   - Seguir comandos en los YAML generados

---

### **Fase 9 (OPCIONAL): Limpieza de Google Cloud** 🗑️

**⚠️ SOLO después de 1-2 semanas de V3 estable en producción:**

```bash
# En Google Cloud Shell
cd backup_scripts
chmod +x 4_optional_cleanup.sh
./4_optional_cleanup.sh
```

Esto elimina servicios antiguos para ahorrar costos.

---

## 🎯 Resultado Final

Después de completar todas las fases:

```
✅ app.aestheticsafe.com → Replit V3 (producción)
✅ app.aestheticsafe.com.ar → V2 (demo/backup)
✅ Backups completos de V1/V2 en Google Cloud
✅ PHI redaction activo en producción
✅ TLS/HTTPS activo
✅ Zero downtime clínico
```

---

## 📞 Soporte

**En caso de problemas:**

1. **Verificar logs en Replit:**
   - Deployments → Logs
   - Buscar errores

2. **Verificar DNS:**
   ```bash
   dig app.aestheticsafe.com +trace
   ```

3. **Contactar soporte:**
   - Replit Support (si problema de deployment)
   - DNS Provider (si problema de propagación)
   - Incluir timestamp y archivos de backup

---

## 📝 Documentación Actualizada

Después de migración exitosa, actualizar:

- [ ] `replit.md` con nueva URL de producción
- [ ] `AUDIT_SUMMARY.md` con dominio actualizado
- [ ] Docs internas con nueva arquitectura
- [ ] Training materials con nueva URL

---

**¡Éxito con la migración!** 🚀

**Dr. Wily Bukret Pesce**  
AestheticSafe® v3.1  
Buenos Aires, Argentina
