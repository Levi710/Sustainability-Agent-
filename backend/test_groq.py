import os
import requests
import json

api_key = os.getenv("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "test"}]
}

res = requests.post(url, headers=headers, json=data)
print(f"Status: {res.status_code}")
print(res.text)
