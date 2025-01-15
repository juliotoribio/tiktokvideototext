from flask import Flask, request, render_template, jsonify
import os
from datetime import datetime
import subprocess
import whisper
import pyktok as pyk

# Configuración de Flask
app = Flask(__name__)

# Define las carpetas
BASE_DIR = os.path.abspath(".")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
MP3_DIR = os.path.join(BASE_DIR, "mp3")

# Crear directorios si no existen
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(MP3_DIR, exist_ok=True)

# Cargar el modelo Whisper
model = whisper.load_model("base")

def transcribe_audio(audio_path):
    """
    Transcribe un archivo de audio utilizando Whisper.
    """
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
    try:
        # Obtener el enlace del formulario
        tiktok_url = request.form.get("tiktok_url")
        if not tiktok_url:
            return jsonify({"error": "No se proporcionó un enlace de TikTok"}), 400

        # Obtener la fecha y hora actual
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Descargar el video
        metadata_path = os.path.join(METADATA_DIR, f"video_metadata_{timestamp}.csv")
        pyk.specify_browser('chrome')
        pyk.save_tiktok(tiktok_url, save_video=True, metadata_fn=metadata_path)

        # Buscar el archivo de video descargado
        video_filename = None
        for file in os.listdir("."):
            if file.endswith(".mp4"):
                video_filename = file
                break

        if not video_filename:
            return jsonify({"error": "No se encontró el archivo de video descargado"}), 500

        # Renombrar el archivo de video
        new_video_filename = f"tiktok_video_{timestamp}.mp4"
        os.rename(video_filename, new_video_filename)

        # Extraer el audio del video
        audio_filename = os.path.join(MP3_DIR, f"tiktok_audio_{timestamp}.mp3")
        command = [
            "ffmpeg",
            "-i", new_video_filename,
            "-q:a", "0",  # Máxima calidad de audio
            "-map", "a",  # Extraer solo la pista de audio
            audio_filename
        ]
        subprocess.run(command, check=True)

        # Transcribir el audio
        transcription = transcribe_audio(audio_filename)

        # Guardar la transcripción
        transcription_filename = os.path.join(MP3_DIR, f"tiktok_transcription_{timestamp}.txt")
        with open(transcription_filename, "w", encoding="utf-8") as f:
            f.write(transcription)

        # Eliminar el video original
        os.remove(new_video_filename)

        # Devolver la transcripción como respuesta
        return jsonify({"transcription": transcription})

    except Exception as e:
        print(f"Error al procesar el video: {e}")
        return jsonify({"error": f"Error al procesar el video: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)