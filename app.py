from flask import Flask, request, jsonify, send_file
import subprocess
import os
import time
import threading

app = Flask(__name__)
UPLOAD_FOLDER = '/app/audios'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"success": True, "service": "Bark TTS", "status": "online"})

@app.route('/tts', methods=['POST'])
def generate_tts():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        lang = data.get('lang', 'pt')
        
        if text.startswith('='):
            text = text[1:].strip()
        
        if not text:
            return jsonify({"success": False, "error": "text required"}), 400
        
        filename = f"audio_{int(time.time() * 1000)}.mp3"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Usa pyttsx3 (mais leve que Bark)
        cmd = f"""python3 << 'PYTHON_SCRIPT'
import pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('voice', 'portuguese')
engine.save_to_file('{text}', '{filepath}')
engine.runAndWait()
PYTHON_SCRIPT
"""
        
        os.system(cmd)
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Falha ao gerar áudio"}), 500
        
        return jsonify({
            "success": True,
            "audioUrl": f"https://viralflowai-coqui-tts-production.up.railway.app/audio/{filename}"
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
        
        time.sleep(5 * 60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
