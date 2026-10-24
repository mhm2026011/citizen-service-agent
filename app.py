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


@app.route("/stt", methods=["POST"])
def stt():
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio"}), 400

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_file.save(tmp.name)

    with open(tmp.name, "rb") as f:
        resp = client.speech_to_text.transcribe(
            file=("audio.wav", f, "audio/wav"),
            model="saaras:v4",
            language_code="unknown",
        )
    os.unlink(tmp.name)
    return jsonify({"transcript": resp.transcript})


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json()
    text = data.get("text", "")[:500]
    lang = data.get("lang", "hi-IN")

    resp = client.text_to_speech.convert(
        text=text,
        language_code=lang,
        speaker="anushka",
        model="bulbul:v2",
    )
    audio_b64 = resp.audio
    return jsonify({"audio_b64": audio_b64})


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("\n  Citizen Services Dashboard running at http://127.0.0.1:5000\n")
    app.run(debug=False, port=5000)