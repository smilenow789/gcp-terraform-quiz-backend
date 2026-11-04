import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import auth, firestore, storage
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

app = Flask(__name__)

# Firebase initialisieren
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# Projekt Konfiguration
PROJECT_ID = os.environ.get("GCP_PROJECT") 
LOCATION = "us-central1" 
# Bucket, in den die Clients ihre PDFs hochladen (per Terraform gesetzt)
PDF_BUCKET = os.environ.get("PDF_BUCKET")

if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

def is_own_upload(gs_link, uid):
    """Erlaubt nur gs://<PDF_BUCKET>/pdfUploads/<uid>/<datei>.

    Verhindert, dass ein Client beliebige Objekte (anderer Nutzer oder
    anderer Buckets) einlesen und anschliessend löschen lässt.
    """
    if not PDF_BUCKET:
        return False
    prefix = f"gs://{PDF_BUCKET}/pdfUploads/{uid}/"
    if not gs_link.startswith(prefix):
        return False
    filename = gs_link[len(prefix):]
    return bool(filename) and "/" not in filename and ".." not in filename

# Auth prüfen
def verify_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "No valid token provided"
    
    id_token = auth_header.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid'], None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"



@app.route('/generate', methods=['POST'])
def generate_questions():
    # 1. Authentifizierung prüfen
    uid, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    # 2. gs_link aus Request holen
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
        
    gs_link = data.get('gs_link') 

    if not gs_link:
        return jsonify({"error": "No 'gs_link' provided"}), 400

    if not isinstance(gs_link, str) or not is_own_upload(gs_link, uid):
        return jsonify({"error": "Invalid 'gs_link'"}), 403

    print(f"Verarbeite File: {gs_link} für User: {uid}")

    try:
        # 3. Vertex AI (Gemini) aufrufen
        model = GenerativeModel("gemini-2.5-flash-lite") 
        
        # PDF aus dem Cloud Storage lesen
        pdf_file = Part.from_uri(uri=gs_link, mime_type="application/pdf")
        
        prompt = """
        Erstelle Multiple-Choice Fragen basierend auf dem Inhalt des angehängten PDF-Dokuments.
        Formatierung: Antworte mit einem validen JSON-Array.
        JSON Struktur pro Frage:
        {
            "Frage": "Der Fragetext hier?",
            "A": "Antwortmöglichkeit 1",
            "B": "Antwortmöglichkeit 2",
            "Korrekt": "A" (oder B)
        }
        """
        generation_config = GenerationConfig(
            response_mime_type="application/json"
        )

        response = model.generate_content(
            [pdf_file, prompt],
            generation_config=generation_config
        )
        
        json_response_text = response.text
        
        questions_json = json.loads(json_response_text)

        # 4. In Firestore speichern (in einer Sub-Collection 'history' unter dem User)
        doc_ref = db.collection('players').document(uid).collection('history').document()
        doc_ref.set({       
            'timestamp': firestore.SERVER_TIMESTAMP,
            'original_filename': gs_link.split('/')[-1],
            'questions': questions_json
        })

        # 5. SICHERES LÖSCHEN
        try:
            # Erwartetes Format: gs://bucket-name/folder/file.pdf
            if gs_link.startswith("gs://"):
                parts = gs_link.split("/")
                
                if len(parts) > 3:
                    bucket_name = parts[2]
                    blob_path = "/".join(parts[3:])
                    
                    bucket = storage.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    
                    # Prüfen ob Datei existiert, bevor löschen
                    if blob.exists():
                        blob.delete()
                        print(f"SUCCESS: Datei gelöscht: {bucket_name}/{blob_path}")
                
        except Exception as delete_error:
            print(f"CRITICAL DELETE ERROR: Konnte PDF nicht löschen: {delete_error}")

        # 6. Antwort zurück an Unity
        return jsonify(questions_json), 200

    except Exception as e:
        print(f"Internal Error: {e}")
        return jsonify({"error": str(e)}), 500

# History abrufen
@app.route('/history', methods=['GET'])
def get_history():
    # 1. Auth prüfen
    uid, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    try:
        # 2. Firestore abfragen
        history_ref = db.collection('players').document(uid).collection('history')
        
        # Sortieren 
        query = history_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
        docs = query.stream()

        history_list = []
        for doc in docs:
            data = doc.to_dict()
            
            ts = data.get('timestamp')
            date_str = ts.isoformat() if ts else ""

            history_list.append({
                "id": doc.id,
                "original_filename": data.get('original_filename', 'Unbekanntes PDF'),
                "date": date_str,
                "questions": data.get('questions', [])
            })

        return jsonify(history_list), 200

    except Exception as e:
        print(f"History Error: {e}")
        return jsonify({"error": str(e)}), 500
    

# DELETE ENDPOINT
@app.route('/delete_history', methods=['DELETE'])
def delete_history():
    # 1. Auth prüfen
    uid, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    # 2. ID aus URL Parameter holen
    doc_id = request.args.get('id')
    try:
        # 3. Dokument löschen
        db.collection('players').document(uid).collection('history').document(doc_id).delete()
        return jsonify({"status": "success", "message": "Entry deleted"}), 200

    except Exception as e:
        print(f"Delete Error: {e}")
        return jsonify({"error": str(e)}), 500



# DELETE COMPLETE ACCOUNT
@app.route('/delete_account', methods=['DELETE'])
def delete_account():
    # A. Token prüfen
    uid, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401
    
    try:
        # B. Firestore History löschen
        history_ref = db.collection('players').document(uid).collection('history')
        docs = history_ref.stream()
        for doc in docs:
            doc.reference.delete()
        
        # C. Firestore User Doc löschen
        db.collection('players').document(uid).delete()

        # D. Auth User löschen
        auth.delete_user(uid)
        
        return jsonify({"status": "success", "message": "Account and all data deleted"}), 200

    except Exception as e:
        print(f"Delete Account Error: {e}")
        return jsonify({"error": str(e)}), 500