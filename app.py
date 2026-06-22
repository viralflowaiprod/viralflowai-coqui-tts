from flask import Flask, request, jsonify, send_file
from TTS.api import TTS
import os
import time
import threading

app = Flask(__name__)

UPLOAD_FOLDER = '/app/audios'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Idiomas
LANGUAGE_MAP = {
    "pt": "pt",
    "pt-BR": "pt",
    "pt-f": "pt",
    "en": "en",
    "es": "es",
    "fr": "fr"
}

# 🔥 HEALTH CHECK
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        "success": True,
        "service": "Coqui TTS",
        "status": "online"
    })

# 🔥 TTS (CORRIGIDO - SEM CRASH NO START)
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

        language = LANGUAGE_MAP.get(lang, "pt")

        print(f"Gerando áudio: {text[:50]}...")

        # 🔥 COQUI CARREGA AQUI (NÃO NO START)
        tts = TTS(model_name="tts_models/pt/cv/glow-tts", gpu=False)

        filename = f"audio_{int(time.time() * 1000)}.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        tts.tts_to_file(
            text=text,
            file_path=filepath,
            language=language
        )

        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "falha ao gerar áudio"}), 500

        mp3_filename = filename.replace(".wav", ".mp3")
        mp3_filepath = os.path.join(UPLOAD_FOLDER, mp3_filename)

        os.system(f"ffmpeg -i {filepath} -q:a 5 {mp3_filepath} -y")

        base_url = os.environ.get(
            "BASE_URL",
            "http://localhost:3000"
        )

        final_file = mp3_filename if os.path.exists(mp3_filepath) else filename

        return jsonify({
            "success": True,
            "audioUrl": f"{base_url}/audio/{final_file}"
        })

    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# 🔥 SERVE AUDIO
@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "file not found"}), 404

    return send_file(filepath, mimetype='audio/mpeg')


# 🔥 CLEANUP
def cleanup():
    while True:
        try:
            now = time.time()
            for f in os.listdir(UPLOAD_FOLDER):
                path = os.path.join(UPLOAD_FOLDER, f)
                if os.path.isfile(path):
                    if time.time() - os.path.getmtime(path) > 1800:
                        os.remove(path)
        except Exception as e:
            print("cleanup error:", e)

        time.sleep(300)


threading.Thread(target=cleanup, daemon=True).start()


# 🔥 START SERVER (CORRIGIDO RAILWAY)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )
