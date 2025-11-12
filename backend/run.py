import os
import sys
import signal

# Ensure the backend folder (this file's directory) is first on sys.path so
# Python imports the local `app` package (backend/app) instead of any
# top-level module named `app.py` in the project root.
BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from config import Config

app = create_app()

def signal_handler(sig, frame):
    print('\n🛑 Shutting down gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    print(f"🚀 Starting AI SQL Chatbot with optimizations:")
    print(f"   - Request timeout: {Config.REQUEST_TIMEOUT}s")
    print(f"   - LLM timeout: {Config.LLM_TIMEOUT}s")
    print(f"   - Cache timeout: {Config.CACHE_TIMEOUT}s")
    print(f"   - Using model: {Config.GEMINI_MODEL}")
    
    app.run(
        debug=True, 
        port=5001,
        threaded=True,  # Enable threading for better performance
        host='0.0.0.0'  # Allow external connections
    )
