import os, base64, tempfile, wave
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()
api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    raise ValueError("SARVAM_API_KEY not found in .env")

client = SarvamAI(api_subscription_key=api_key)

app = Flask(__name__)
app.secret_key = os.urandom(24)

SYSTEM_PROMPT = (
    "You are a helpful Citizen Services Agent for Indian citizens. "
    "Answer queries about government schemes (PM-KISAN, Ayushman Bharat, MGNREGA, etc.), "
    "taxes, pensions, birth/death/caste certificates, and Aadhaar/PAN services. "
    "Guide users step-by-step through application processes. "
    "Be concise, warm and helpful. Keep responses under 100 words. "
    "If the user writes in Hindi or another Indian language, respond in that language."
)


def get_history():
    if "history" not in session:
        session["history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return session["history"]


@app.route("/")
def index():
    session.clear()
    return render_template("dashboard.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_text = data.get("text", "").strip()
        if not user_text:
            return jsonify({"error": "Empty message"}), 400

        history = get_history()
        history.append({"role": "user", "content": user_text})

        resp = client.chat.completions(messages=history, model="sarvam-105b-conversations")
        reply = resp.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        session["history"] = history
        session.modified = True
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stt", methods=["POST"])
def stt():
    try:
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"error": "No audio file received"}), 400

        # Detect format from browser (MediaRecorder sends webm)
        ext = ".webm" if "webm" in (audio_file.content_type or "") else ".wav"
        mime = "audio/webm" if ext == ".webm" else "audio/wav"

        # On Windows, delete=False + explicit close is required to avoid WinError 32
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp_path = tmp.name
        audio_file.save(tmp_path)
        tmp.close()  # Must close before re-opening on Windows

        try:
            with open(tmp_path, "rb") as f:
                resp = client.speech_to_text.transcribe(
                    file=(f"audio{ext}", f, mime),
                    model="saaras:v4",
                    language_code="unknown",
                )
            transcript = resp.transcript or ""
        finally:
            try:
                os.unlink(tmp_path)  # Clean up even if transcription fails
            except Exception:
                pass

        return jsonify({"transcript": transcript})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tts", methods=["POST"])
def tts():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()[:500]
        lang = data.get("lang", "hi-IN")
        if not text:
            return jsonify({"error": "Empty text"}), 400

        resp = client.text_to_speech.convert(
            text=text,
            language_code=lang,
            speaker="ritu",
            model="bulbul:v3",
        )
        audio_b64 = resp.audios[0]
        return jsonify({"audio_b64": audio_b64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("\n  Citizen Services Dashboard running at http://127.0.0.1:5000\n")
    app.run(debug=False, port=5000)