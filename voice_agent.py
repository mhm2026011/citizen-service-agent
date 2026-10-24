import os, base64, tempfile, wave, pyaudio
from dotenv import load_dotenv
from sarvamai import SarvamAI
from playsound import playsound

load_dotenv()
api_key = os.getenv('SARVAM_API_KEY')
if not api_key:
    raise ValueError('SARVAM_API_KEY not found in .env')

client = SarvamAI(api_subscription_key=api_key)

SYSTEM_PROMPT = (
    'You are a helpful Citizen Services Agent for Indian citizens. '
    'Answer queries about government schemes, taxes, pensions, and certificates. '
    'Guide users step-by-step. Be concise, warm, and helpful. '
    'If the user speaks in Hindi or another Indian language, respond in that same language.'
)

conversation_history = [{'role': 'system', 'content': SYSTEM_PROMPT}]

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5


def record_audio():
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    print('  [Recording for 5 seconds... speak now]')
    frames = [stream.read(CHUNK) for _ in range(int(RATE / CHUNK * RECORD_SECONDS))]
    stream.stop_stream()
    stream.close()
    pa.terminate()
    print('  [Done recording]')
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    wf = wave.open(tmp.name, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return tmp.name


def speech_to_text(wav_path):
    with open(wav_path, 'rb') as f:
        resp = client.speech_to_text.transcribe(
            file=('audio.wav', f, 'audio/wav'),
            model='saaras:v4',
            language_code='unknown',
        )
    return resp.transcript


def chat(user_text):
    conversation_history.append({'role': 'user', 'content': user_text})
    resp = client.chat.completions(
        messages=conversation_history,
        model='sarvam-105b-conversations',
    )
    reply = resp.choices[0].message.content
    conversation_history.append({'role': 'assistant', 'content': reply})
    return reply


def text_to_speech(text):
    resp = client.text_to_speech.convert(
        text=text,
        language_code='hi-IN',
        speaker='ritu',
        model='bulbul:v3',
    )
    audio_bytes = base64.b64decode(resp.audios[0])
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.write(audio_bytes)
    tmp.flush()
    tmp.close()
    playsound(tmp.name)
    os.unlink(tmp.name)


def run():
    print('=' * 50)
    print('  Citizen Services Voice Agent')
    print('  Supports: Hindi, English, Regional langs')
    print('=' * 50)
    print("Type your query, press ENTER to use mic, or 'quit' to exit\n")
    while True:
        mode = input('You (ENTER=mic): ').strip()
        if mode.lower() == 'quit':
            print('Goodbye!')
            break
        if mode == '':
            wav_path = record_audio()
            user_text = speech_to_text(wav_path)
            os.unlink(wav_path)
            if not user_text.strip():
                print('  Could not understand. Try again.\n')
                continue
            print(f'  You said: {user_text}')
        else:
            user_text = mode
        print('  Thinking...')
        reply = chat(user_text)
        print(f'\n  Agent: {reply}\n')
        print('  Speaking...')
        try:
            text_to_speech(reply)
        except Exception as e:
            print(f'  [TTS error: {e}]')


if __name__ == '__main__':
    run()