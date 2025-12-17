# Cloud Programming Infrastructure (GCP)

Dieses Repository enthält **Infrastructure as Code (IaC)** auf Basis von **Terraform**, um das Backend für eine **Unity-Applikation (Client)** auf der **Google Cloud Platform (GCP)** bereitzustellen.

---

## 📋 Voraussetzungen

Vor dem Deployment müssen folgende Tools installiert und konfiguriert sein:

* **Terraform CLI**
* **Google Cloud SDK (gcloud)**
* **Aktives Google Cloud Projekt** mit verknüpftem Rechnungskonto

**Nützliche Links:**
* [Terraform Download](https://developer.hashicorp.com/terraform/downloads)
* [Google Cloud SDK Installation](https://cloud.google.com/sdk/docs/install)

---

## ⚙️ Konfiguration

Erstellen Sie im Root-Verzeichnis eine Datei `terraform.tfvars`, um projektspezifische Variablen zu definieren.

### Beispiel: `terraform.tfvars`

```hcl
project_id           = "ihre-gcp-projekt-id"
region               = "us-central1"
android_package_name = "com.ihrname.cloudprogramming"
android_sha1_hashes  = ["SHA1-HASH-IHRES-KEYSTORES"]
```

### Variablenbeschreibung

| Variable               | Beschreibung                                   |
|------------------------|-----------------------------------------------|
| `project_id`           | ID des Google Cloud Projekts                  |
| `region`               | GCP-Region für das Deployment                 |
| `android_package_name` | Paketname der Android-App (Unity)             |
| `android_sha1_hashes`  | Liste der SHA-1 Fingerprints für Firebase Auth|

---

## Deployment Anleitung

Führen Sie die folgenden Schritte im Terminal aus:

### 1. Authentifizierung

Melden Sie sich bei der Google Cloud CLI an und setzen Sie das Application Default Login:

```bash
gcloud auth login
gcloud auth application-default login
```

Setzen Sie das Quota-Projekt (wichtig für Terraform API-Calls).

```PowerShell
$env:GOOGLE_CLOUD_QUOTA_PROJECT = "ihre-projekt-id"
```

### 2. Initialisierung

Laden Sie die notwendigen Provider (google, google-beta) herunter:

```bash
terraform init
```

### 3. Deployment (Apply)

Erstellen Sie die Infrastruktur. Dieser Schritt baut auch automatisch den Docker-Container und lädt ihn hoch.

```bash
terraform apply
```

**Hinweis:**  
Das Deployment kann einige Minuten dauern, da erforderliche APIs aktiviert werden müssen. Eine *time_sleep*-Ressource ist integriert, um Race-Conditions zu vermeiden.

---

## Outputs

Nach erfolgreichem Durchlauf gibt Terraform folgende Werte aus, die in Unity eingetragen werden müssen:

- **cloud_run_url** – URL des Backends  
  (z. B. https://cloud-programming-service-...run.app)
- **bucket_name** – Name des Storage Buckets für PDFs
- **firestore_database_id** – ID der Datenbank

---

## Clean Up

Um alle erstellten Ressourcen zu löschen und Kosten zu vermeiden, führen Sie folgenden Befehl aus:
```bash
terraform destroy
```

---

## 📂 Projektstruktur

```plaintext
.
├── backend/                # Source Code für den Cloud Run Container
│   ├── main.py             # Flask Applikation
│   ├── Dockerfile          # Container Definition
│   └── requirements.txt    # Python Abhängigkeiten
├── main.tf                 # Hauptkonfiguration (Resources, Provider, Data)
├── variables.tf            # Variablendefinitionen
├── outputs.tf              # Rückgabewerte
├── firestore.rules         # Sicherheitsregeln für Datenbank
├── storage.rules           # Sicherheitsregeln für Dateispeicher
├── terraform.tfvars        # (Nicht im Git) Persönliche Konfigurationswerte
└── README.md               # Diese Datei
```
