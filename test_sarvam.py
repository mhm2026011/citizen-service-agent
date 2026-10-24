import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

api_key = os.getenv('SARVAM_API_KEY')
if not api_key:
    raise ValueError('SARVAM_API_KEY not found in .env')

client = SarvamAI(api_subscription_key=api_key)

response = client.chat.completions(
    messages=[{'role': 'user', 'content': 'Hello! What services can you help me with?'}],
    model='sarvam-105b-conversations',
)

print(response.choices[0].message.content)
