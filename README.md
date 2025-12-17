Cloud Programming Infrastructure (GCP)
Dieses Repository enthält den Infrastructure as Code (IaC) Code basierend auf Terraform, um das Backend für die Unity-Applikation (Client) auf der Google Cloud Platform (GCP) bereitzustellen.


Voraussetzungen
Bevor das Deployment gestartet werden kann, müssen folgende Tools installiert sein:
- Terraform CLI
- Google Cloud SDK (gcloud)
- Ein aktives Google Cloud Projekt mit verknüpftem Rechnungskonto.


Konfiguration
Erstellen Sie im Root-Verzeichnis eine Datei namens terraform.tfvars, um die Variablen zu definieren.
Beispiel terraform.tfvars:
project_id           = "ihre-gcp-projekt-id"
region               = "us-central1"
android_package_name = "com.ihrname.cloudprogramming"
android_sha1_hashes  = ["SHA1-HASH-IHRES-KEYSTORES"]


Variablen Beschreibung
project_id -> Die ID des Google Cloud Projekts.
region -> Die GCP Region für das Deployment.
android_package_name -> Der Paketname der Android App (aus Unity).
android_sha1_hashes -> Liste der SHA-1 Fingerprints für Firebase Auth.


Deployment Anleitung
Führen Sie folgende Schritte in deinem Terminal aus:
1. Authentifizierung
    Melden Sie sich bei der Google Cloud CLI an und setzen Sie das Application Default Login:
        gcloud auth login
        gcloud auth application-default login
    Setzen Sie das Quota-Projekt (wichtig für Terraform API-Calls) - (Windows PowerShell):
        $env:GOOGLE_CLOUD_QUOTA_PROJECT = "ihre-projekt-id"
2. Initialisierung
    Laden Sie die notwendigen Provider (google, google-beta) herunter:
        terraform init
3. Deployment (Apply)
    Erstellen Sie die Infrastruktur. Dieser Schritt baut auch automatisch den Docker-Container und lädt ihn hoch.
        terraform apply

Hinweis: Das Deployment kann einige Minuten dauern, da APIs aktiviert werden müssen (time_sleep Ressource ist integriert, um Race-Conditions zu vermeiden).


Outputs
Nach erfolgreichem Durchlauf gibt Terraform folgende Werte aus, die in Unity eingetragen werden müssen:
    cloud_run_url: Die URL des Backends (z. B. https://cloud-programming-service-...run.app).
    bucket_name: Der Name des Storage Buckets für PDFs.
    firestore_database_id: Die ID der Datenbank.


Clean Up
Um alle erstellten Ressourcen zu löschen und Kosten zu vermeiden:
    terraform destroy


Projektstruktur

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