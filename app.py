from flask import Flask, request, jsonify, send_file
from TTS.api import TTS
import os
import uuid
from datetime import datetime
import threading
import time

app = Flask(__name__)
UPLOAD_FOLDER = '/app/audios'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicializa Coqui TTS
print("Carregando Coqui TTS...")
tts = TTS(model_name="tts_models/pt/cv/tacotron2-DDC", progress_bar=True, gpu=False)
print("Coqui TTS pronto!")

# Map de idiomas
LANGUAGE_MAP = {
    "pt": "pt",
    "pt-BR": "pt",
    "pt-f": "pt",
    "en": "en",
    "en-US": "en",
    "es": "es",
    "es-ES": "es",
    "fr": "fr",
    "fr-FR": "fr",
    "de": "de",
    "de-DE": "de",
    "it": "it",
    "it-IT": "it"
}

@app.route('/', methods=['GET'])
def health():
    return jsonify({"success": True, "service": "Coqui TTS", "status": "online"})

@app.route('/tts', methods=['POST'])
def generate_tts():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        lang = data.get('lang', 'pt')
        
        # Remove = se vier do n8n
        if text.startswith('='):
            text = text[1:].strip()
        
        if not text:
            return jsonify({"success": False, "error": "text required"}), 400
        
        # Map idioma
        language = LANGUAGE_MAP.get(lang, "pt")
        
        # Gera arquivo único
        filename = f"audio_{int(time.time() * 1000)}.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        print(f"Gerando áudio: {text[:50]}... em {language}")
        
        # Gera TTS
        tts.tts_to_file(
            text=text,
            file_path=filepath,
            language=language,
            verbose=False
        )
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Falha ao gerar áudio"}), 500
        
        # Converte WAV pra MP3 (opcional, but better)
        mp3_filename = filename.replace('.wav', '.mp3')
        mp3_filepath = os.path.join(UPLOAD_FOLDER, mp3_filename)
        
        os.system(f"ffmpeg -i {filepath} -q:a 5 {mp3_filepath} -y 2>/dev/null")
        
        if os.path.exists(mp3_filepath):
            os.remove(filepath)
            return jsonify({
                "success": True,
                "audioUrl": f"http://localhost:3000/audio/{mp3_filename}"
            })
        
        return jsonify({
            "success": True,
            "audioUrl": f"http://localhost:3000/audio/{filename}"
        })
    
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "file not found"}), 404
        return send_file(filepath, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Auto-delete arquivos antigos (30 min)
def cleanup_old_files():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(UPLOAD_FOLDER):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    if now - os.path.getmtime(filepath) > 30 * 60:
                        os.remove(filepath)
                        print(f"Deletado: {filename}")
        except Exception as e:
            print(f"Erro cleanup: {e}")
        
        time.sleep(5 * 60)  # Checa a cada 5 minutos

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
