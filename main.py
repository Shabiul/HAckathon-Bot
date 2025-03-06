import logging
from flask import Flask, render_template
from bot import run_bot
import threading
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

@app.route('/')
def index():
    """Route for bot status page"""
    return render_template('index.html')

def run_flask():
    """Function to run Flask app"""
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Run Flask app in the main thread
    run_flask()