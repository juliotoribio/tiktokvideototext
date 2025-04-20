from flask import Flask, request, render_template, jsonify
import os
from datetime import datetime
import subprocess
import whisper
import pyktok as pyk

# Configuración de Flask
app = Flask(__name__)

# Define carpetas
BASE_DIR = os.path.abspath(".")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
MP3_DIR = os.path.join(BASE_DIR, "mp3")

# Crear directorios si no existen
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(MP3_DIR, exist_ok=True)

# Cargar el modelo Whisper
model = whisper.load_model("base")

def transcribe_audio(audio_path):
    """Transcribe un archivo de audio usando Whisper."""
    try:
        result = model.transcribe(audio_path, fp16=False)
        return result["text"]
    except Exception as e:
        print(f"Error al transcribir el audio: {e}")
        return None

@app.route("/")
def index():
    """Renderiza la página principal."""
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process_video():
    """Procesa el video de TikTok y devuelve la transcripción."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    metadata_path = os.path.join(METADATA_DIR, f"video_metadata_{timestamp}.csv")
    audio_filename = os.path.join(MP3_DIR, f"tiktok_audio_{timestamp}.mp3")
    transcription_filename = os.path.join(MP3_DIR, f"tiktok_transcription_{timestamp}.txt")
    new_video_filename = f"tiktok_video_{timestamp}.mp4"

    try:
        # Obtener URL de TikTok
        tiktok_url = request.form.get("tiktok_url")
        if not tiktok_url:
            return jsonify({"error": "No se proporcionó un enlace de TikTok"}), 400

        # Descargar video
        pyk.specify_browser('chrome')
        pyk.save_tiktok(tiktok_url, save_video=True, metadata_fn=metadata_path)

        # Buscar video descargado
        video_filename = None
        for file in os.listdir("."):
            if file.endswith(".mp4"):
                video_filename = file
                break

        if not video_filename:
            return jsonify({"error": "No se encontró el archivo de video descargado"}), 500

        os.rename(video_filename, new_video_filename)

        # Extraer audio con ffmpeg
        command = [
            "ffmpeg",
            "-i", new_video_filename,
            "-q:a", "0",
            "-map", "a",
            audio_filename
        ]
        subprocess.run(command, check=True)

        # Transcripción
        transcription = transcribe_audio(audio_filename)

        if not transcription:
            return jsonify({"error": "No se pudo transcribir el audio"}), 500

        # Guardar transcripción si quieres mantenerla
        with open(transcription_filename, "w", encoding="utf-8") as f:
            f.write(transcription)

        return jsonify({"transcription": transcription})

    except Exception as e:
        print(f"Error al procesar el video: {e}")
        return jsonify({"error": f"Error al procesar el video: {str(e)}"}), 500

    finally:
        # Eliminar archivos temporales
        for path in [new_video_filename, audio_filename, transcription_filename, metadata_path]:
            if os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    app.run(debug=True)
