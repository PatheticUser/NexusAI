"""Flask entry point — run this to start NexusAI."""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"\n🚀  NexusAI is running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
