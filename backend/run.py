from app import create_app
from config import Config
import signal
import sys

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
