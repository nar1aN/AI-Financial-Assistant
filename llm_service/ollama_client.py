import requests
import json
import re
from typing import Any

ollama_url = 'http://localhost:11434/api/genarate'
model_name = 'qwen2.5:7b'

def _extract_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("Could not extract json from {}".format(text))

def ask_ollama(promt: str, retries: int = 3) -> dict[str, Any]:
    payload = {
        "model": model_name,
        "promt": promt,
        "stream": False,
        "temperature": 0.1,
        "options": {"num_predict": 256}
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                ollama_url, json = payload, timeout = 60
            )
            response.raise_for_status()
            raw_text = response.json()["response"]
            return _extract_json(raw_text)

        except (ValueError, KeyError) as e:
            #change print to logging when logger will connect
            print(f"[ollama_client] attempt {attempt + 1}: failed -- {e}")

        except requests.RequestException as e:
            print(f"[ollama_client] Connection to ollama error: {e})
            break
    return {"error" : "ollama_unavailable"}

def is_available() -> bool: #fast checking that ollama has started successfully
    try:
        r = requests.get("http://localhost:11434", timeout = 5)
        return r.status_code == 200
    except requests.RequestException:
        return False
