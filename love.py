import os
from flask import Flask, request, jsonify, render_template, session
from openai import OpenAI
from datetime import datetime
from flask_session import Session  # Server-side sessions
from dotenv import load_dotenv

# Load .env if present (safe for dev)
load_dotenv()

# Load environment variables (Render or local)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set. Add it to Render Environment Variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Optional logging
LOG_FILE = "chat_log.txt"

def log_message(user_message, bot_reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] USER: {user_message}\n[{timestamp}] BOT: {bot_reply}\n\n")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "message required"}), 400

    # Initialize session memory
    if "messages" not in session:
        session["messages"] = []
    if "history" not in session:
        session["history"] = []

    # Multilingual warm system prompt
    system_prompt = (
        "You are a warm, empathetic, supportive, and non-judgmental chatbot that ONLY talks about "
        "love, relationships, emotions, romance, trust, heartbreak, and human connection. "
        "You can understand any language the user writes in and always respond in the same language. "
        "If a user asks anything unrelated (math, programming, politics, sports, etc.), politely refuse "
        "and remind them that you only answer love and relationship topics. "
        "If the user expresses self-harm or danger, advise them to seek professional help immediately, "
        "and provide general safety guidance."
    )

    if not session["messages"]:
        session["messages"].append({"role": "system", "content": system_prompt})

    # Save user msg
    session["messages"].append({"role": "user", "content": user_message})
    session["history"].append({"sender": "user", "text": user_message})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # lightweight and fast
            messages=session["messages"],
            max_tokens=500,
            temperature=0.8
        )
        bot_reply = resp.choices[0].message.content

        # Save bot reply
        session["messages"].append({"role": "assistant", "content": bot_reply})
        session["history"].append({"sender": "bot", "text": bot_reply})

        # Optional logging
        log_message(user_message, bot_reply)

        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"reply": f"Oops! Something went wrong: {str(e)}"})

# Clear chat session (but keep history)
@app.route("/clear", methods=["POST"])
def clear_chat():
    session.pop("messages", None)
    return jsonify({"status": "cleared"})

# Return chat history
@app.route("/history", methods=["GET"])
def get_history():
    history = session.get("history", [])
    return jsonify(history)

if __name__ == "__main__":
    # Use dynamic port for Render hosting
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # debug=False for production
