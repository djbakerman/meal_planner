
import json
import requests
import os
from typing import Optional, List, Dict, Any, Union
from . import config

def is_claude_model(model: str) -> bool:
    """Check if the model is a Claude model."""
    """Check if the model is a Claude model."""
    if not model:
        return False
    return any(cm in model for cm in config.CLAUDE_MODELS) or model.startswith("claude-")

def query_ollama(prompt: str, model: str = config.DEFAULT_OLLAMA_MODEL, 
                 images: List[str] = None, json_mode: bool = False) -> Optional[str]:
    """Send a prompt (text or vision) to Ollama."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1 if images else 0.7,
            "num_predict": 4096
        }
    }
    
    if images:
        payload["images"] = images
    
    # Note: Ollama doesn't support 'format': 'json' reliably across all models yet, 
    # so we rely on prompt engineering, but functionality is there if needed
    if json_mode:
        payload["format"] = "json"
        
    try:
        response = requests.post(config.OLLAMA_API_URL, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Ollama at {config.OLLAMA_API_URL}")
        return None
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return None

def query_claude(prompt: str, model: str, api_key: str = None, 
                images: List[Dict[str, str]] = None) -> Optional[str]:
    """
    Send a prompt to Claude API.
    images kwarg expects list of dicts: {'media_type': 'image/jpeg', 'data': 'base64str'}
    """
    key = api_key or config.ANTHROPIC_API_KEY
    if not key:
        print("Error: Claude API key required.")
        return None
        
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01"
    }
    
    content = []
    
    # Add images if provided
    if images:
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.get("media_type", "image/jpeg"),
                    "data": img["data"]
                }
            })
            
    # Add text prompt
    content.append({
        "type": "text",
        "text": prompt
    })
    
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": content}
        ]
    }
    
    try:
        response = requests.post(config.CLAUDE_API_URL, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            print(f"Error: Claude API returned {response.status_code}: {response.text[:200]}")
            return None
        
        result = response.json()
        return result.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Error querying Claude: {e}")
        return None

def query_llm(prompt: str, model: str = None, api_key: str = None, 
              images: List[Any] = None, json_mode: bool = False) -> Optional[str]:
    """Generic wrapper to query either Ollama or Claude."""
    if model is None:
        model = config.DEFAULT_MODEL

    if is_claude_model(model):
        # Format images for Claude if present (assuming they are passed as raw base64 or dicts)
        # This wrapper expects caller to handle specific format adaptation or use specific functions
        # For simplicity, if generic query_llm is called with images, we assume they need adaptation
        # But generally, it's better to call the specific function if you have complex image needs
        return query_claude(prompt, model, api_key, images)
    else:
        # For Ollama, images should be a list of base64 strings
        ollama_images = []
        if images:
            # Logic to extract base64 from dict if passed in Claude format
            for img in images:
                if isinstance(img, dict) and "data" in img:
                    ollama_images.append(img["data"])
                elif isinstance(img, str):
                    ollama_images.append(img)
                    
        return query_ollama(prompt, model, ollama_images, json_mode=json_mode)

def parse_json_response(response: str) -> Optional[dict]:
    """Safely parse JSON from model response, handling markdown code blocks."""
    if not response:
        return None
    
    json_str = response.strip()
    
    # Handle markdown code blocks
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        parts = json_str.split("```")
        if len(parts) >= 2:
            json_str = parts[1]
    
    try:
        return json.loads(json_str.strip())
    except json.JSONDecodeError:
        return None
