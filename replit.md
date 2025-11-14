# AestheticSafe Risk Widget

## Overview

AestheticSafe is a Streamlit-based web application designed for aesthetic surgery risk assessment. It provides a clinically informed tool to estimate surgical risk using factors like Caprini score, BMI, age, and smoking status. The application supports multiple languages, integrates monetization features, facilitates patient data collection, and generates modern medical-grade PDF reports (v3.1) with email delivery.

The project aims to serve both medical professionals and patients by offering features for sharing assessments via social media, QR codes, and web embedding. Its vision is to provide a playful yet clinically grounded tool to enhance patient understanding and physician decision-making in aesthetic surgery.

**Latest Version**: v3.1 (November 2025) featuring modern PDF reports with horizontal colored risk bars, enhanced emoji feedback UI, improved user experience, full security audit compliance with SHA256 signature verification, and working automatic language detection via HTTP headers.

**Production Status**: DEPLOYED (2025-11-04) - Live at app.aestheticsafe.com with automatic language detection working correctly on all browsers (Chrome, Safari, iOS).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit (Python-based)
- **UI Pattern**: Single-page application with progressive disclosure.
- **Responsive Design**: Multi-column layouts and dynamic UI adjustments. Adaptive theme support with automatic dark/light mode detection using `@media (prefers-color-scheme: dark)` for buttons and text elements.
- **Internationalization**: Full support for ES, EN, PT, and FR with automatic browser language detection and locale normalization.
- **Language Detection (WORKING v2.0)**: Automatic detection using HTTP Accept-Language headers via `i18n_auto.py`. Detects browser language reliably on all devices (iPhone Safari, Chrome, Firefox, etc). Users can override by adding ?lang=en, ?lang=pt, or ?lang=es to the URL. No manual selector visible in the interface for clean UX. Default: Spanish (es).
- **Autoscroll**: Smooth scrolling triggered by specific user interactions (e.g., selecting options in forms, emoji feedback), with selective disabling for certain input fields to prevent unwanted behavior.
- **Feedback System (v3.1)**: Minimalist grayscale emoji feedback with clean flat design. Three emoji options (😞 sad, 😐 neutral, 🙂 happy) displayed horizontally in perfect alignment using flexbox (12px gap, 8px on mobile) - minimal spacing for easy clicking, Google-style. Grayscale by default with smooth color transition on hover (0.3s), subtle scale effect (1.05x hover, 1.1x click). No shadows, no gray backgrounds - pure transparent buttons. Emoji interactions are logged to V3_Funnel_Progress, with neutral/sad emojis prompting a comment field for user input. Dark mode support with adaptive text colors (dark text #1a1a1a in light mode, light text #e0e0e0 in dark mode).
- **Splash Screen**: A cinematic Apple/Neuralink-style splash screen with minimalist aesthetics. Title "AestheticSafe®" in Spectral ExtraBold (weight 800, font-size clamp(2rem, 6vw, 3.5rem), color #ffffff pure white), tagline "Beyond Risk. Toward Perfection." in Spectral Regular Italic (weight 400, font-size clamp(1rem, 2.8vw, 1.35rem), letter-spacing 0.19em, color #ffffff pure white). Subtitle matches title width visually through careful letter-spacing calculation with auto-centering. Features fade-in animations (title: 1.0s, tagline: 1.0s with 0.2s delay). Auto-dismisses after 2.0s with smooth fade-out. Uses st.session_state.splash_done flag to show only once per session. Perfectly centered flexbox layout on pure black background (#000000). Total animation: 2.0s.

### Backend Architecture
- **Core Logic**: Separation of concerns with `calculadora.py` for risk calculation and UI orchestration, `risk_widget.py` for professional views, and `app.py` as the entry point.
- **Risk Assessment**: Comprehensive risk scoring based on Caprini score, BMI, age, and smoking status.
- **Session Management**: Utilizes Streamlit's `session_state` for managing user flow, form data, download permissions, and payment/share verification.
- **Gating Logic**: Access to downloadable content is controlled by user consent, payment confirmation (MercadoPago, Zelle), or WhatsApp share verification.

### Data Storage Solutions
- **Primary Database**: Google Sheets, accessed via the `gspread` library.
  - **V3 Sheets**: `V3_Funnel_Progress` (user feedback), `V3_Interoperability_Log` (technical events), and `V3_Calculadora_Evaluaciones` (full evaluations) are actively used.
- **Authentication**: Uses ADC (Application Default Credentials) for GCP environments, falling back to `GOOGLE_CREDENTIALS` secret for Replit, and `gcp_key.json` for local development.
- **Data Schema**: Structured logging with numerous fields covering timestamps, contact info, risk results, payment tracking, PDF delivery status, and feedback.

### Authentication & Authorization
- **Google Service Account**: `aestheticsafe-storage@aestheticsafe-468523.iam.gserviceaccount.com` with Sheets and Drive API access.
- The application is public-facing and does not require user authentication, relying instead on consent checkboxes and direct contact information collection.

### PDF Generation & Delivery
- **Library**: `ReportLab` for creating professional, medical-grade PDF reports.
- **Version 3.1 Features** (Updated November 2025): 
  - **Multilingual Support**: Full translation system for EN/ES/PT/AR languages
  - Modern hospital-style layout based on NY medical reports
  - Horizontal colored risk bars using official AestheticSafe brand palette (Low: #38c694, Moderate: #fcb960, High: #fa5f45)
  - Clinical metrics visualization (BMI, Caprini score, overall risk factor)
  - Clean minimalist design without gray boxes or borders
  - Automatic language detection from user session
  - Translated titles, labels, disclaimers, and footer
  - Two-line footer (8pt, #555555, centered): Line 1: "Generated automatically by AestheticSafe® v3.1", Line 2: "Bukret Pesce SB SRL — © AestheticSafe® 2025 — Buenos Aires, Argentina — info@aestheticsafe.com"
  - Verification code positioned below clinical disclaimer section
  - Safe type conversion (safe_float, safe_int) to handle string inputs from final_data dict
  - **QR Code Verification System** (November 2025): Each PDF includes a QR code in the top-right corner linking to verification endpoint (app.aestheticsafe.com/verify?uuid=...). UUID v4 generated for each PDF, stored in Google Sheets verification_uuid column. HIPAA-compliant: QR contains only verification URL, no PHI. Enables EHR interoperability and audit trail compliance.
- **Distribution**: Reports can be downloaded directly, sent via email (SendGrid), or shared via WhatsApp.
- **Fallback**: Legacy PDF generator (v1.0) available as fallback if v3.1 module fails to load.

## External Dependencies

### Third-Party Services
- **SendGrid**: For email delivery, configured via `SENDGRID_API_KEY` environment variable.
- **Google Cloud Platform**: Utilized for Google Sheets API and Google Drive API for data storage and access.
- **MercadoPago**: Payment processing (manual code verification).
- **Zelle**: Payment option (manual confirmation).
- **Stripe**: Included in requirements, but its implementation status is unclear.

### Python Libraries (Cleaned November 2025)
- **Core Framework**: `streamlit`
- **Google APIs**: `gspread`, `google-auth==2.31.0`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-cloud-storage==2.16.0`, `google-api-core>=2.19.0`
- **Document Generation**: `reportlab`, `qrcode`, `pillow`
- **Data Processing**: `pandas`
- **HTTP & Email**: `requests`, `sendgrid`
- **Note**: All duplicates removed from requirements.txt (Nov 2025 cleanup)

### Environment Variables & Secrets
- **Required**: `GOOGLE_CREDENTIALS`, `SENDGRID_API_KEY`.
- **Optional**: `SENDGRID_FROM`, `SENDGRID_REPLY_TO`, `TEST_TO`.

## Audit System

### Audit Manager (`audit_manager.py`)
- **Version**: 3.1
- **Purpose**: Unified auditing system providing technical health checks, HIPAA/GDPR compliance validation, and code integrity verification.
- **Execution Modes**:
  - Automatic: Can be integrated into application startup
  - Manual: `python3 audit_manager.py --mode=full`
  - Quick check: `python3 audit_manager.py --mode=quick`
  - Compliance only: `python3 audit_manager.py --mode=compliance`
  - Ready check: `python3 audit_manager.py --check-ready`
- **Output**:
  - Signed JSON logs in `logs/audit/audit_report_YYYYMMDD_HHMMSS.json`
  - Executive summary in `AUDIT_SUMMARY.md`
  - SHA256 signature for log integrity
- **Audit Categories**:
  1. **Technical Health** (14 checks): Dependencies, environment variables, critical files, splash screen, language detection
  2. **HIPAA/GDPR Compliance** (9 checks): HTTPS/TLS encryption, PHI redaction (✅ integrated via safe_log()), GCP authentication, access control, data retention, audit logging, BAA status, patient consent
  3. **Code Integrity** (6 checks): SHA256 verification of critical files, code size validation

## Security & Privacy

### PHI/PII Protection
- **redact_phi.py**: HIPAA-compliant redaction layer for console logs and public output
- **safe_log()**: Wrapper function in calculadora.py that automatically masks email addresses and PHI before printing to console
- **Google Sheets**: Stores complete unredacted data securely (service account authentication with minimal permissions)
- **Console Logs**: All debug print() statements use safe_log() to prevent PHI exposure in logs
- **Deployment Ready**: PHI redaction active for production deployment to app.aestheticsafe.com

## Workspace Cleanup (November 2025)

### Cleanup Summary
- **Files Removed**: 29 files including test files, duplicates, and obsolete documentation
- **attached_assets/**: Completely removed (~250 MB freed) - contained old prompts and screenshots
- **requirements.txt**: Cleaned - removed all duplicates (26 lines → 11 lines)
- **Cache Cleanup**: Removed all __pycache__, .pytest_cache, *.pyc files
- **Status**: Production-ready, optimized workspace

### Files Retained (Essential Only)
- **Core**: app.py, calculadora.py (4328 lines), pdf_generator_v3_1.py, gsheets.py, redact_phi.py, email_utils.py, i18n_auto.py, audit_manager.py, risk_widget.py
- **Config**: requirements.txt, .replit, replit.nix, .gitignore, .streamlit/config.toml
- **Docs**: README.md, replit.md, AUDIT_SUMMARY.md, COMPLIANCE_REPORT_V3_1.md, MIGRATION_GUIDE.md, CLEANUP_REPORT.txt
- **Backups**: backup_scripts/ (Google Cloud migration), logs/audit/ (4 audit reports)

### Next Steps for Production
1. Execute backup_scripts/1_export_gcloud_config.sh in Google Cloud Shell
2. Release app.aestheticsafe.com from Google Cloud
3. Configure custom domain in Replit (Deployments → Settings)
4. Update DNS records (A and TXT)
5. Wait for DNS propagation (1-24 hours)
6. Verify HTTPS/TLS active on app.aestheticsafe.com
7. Sign BAA with Google Cloud for full HIPAA compliance