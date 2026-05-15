import os
from dotenv import load_dotenv
from app.agents.pipeline import _raw_llm_call, _get_api_key

load_dotenv()
api_key = _get_api_key()
print(f'Key loaded: {"Yes" if api_key else "No"}')
if api_key:
    try:
        response = _raw_llm_call(api_key, 'You are a helpful assistant.', 'Say The API is working!')
        print('API Response:', response)
    except Exception as e:
        print('Error:', e)
