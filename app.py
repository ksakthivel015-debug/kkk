import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

import chatbot_config as config

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"
MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_LENGTH = 2000

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def build_contents(messages):
    """Convert the chat history from the browser into Gemini contents."""
    contents = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        text = str(message.get("content", "")).strip()[:MAX_MESSAGE_LENGTH]
        if not text:
            continue
        role = "user" if message.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))

    # Gemini expects the conversation to start with a user message.
    while contents and contents[0].role != "user":
        contents.pop(0)

    return contents


@app.route("/")
def index():
    return render_template(
        "index.html",
        name=config.CHATBOT_NAME,
        title=config.CHATBOT_TITLE,
        icon=config.CHATBOT_ICON,
        theme_color=config.THEME_COLOR,
        welcome_message=config.WELCOME_MESSAGE,
        suggestions=config.SUGGESTIONS,
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    contents = build_contents(data.get("messages", []))

    if not contents or contents[-1].role != "user":
        return jsonify({"error": "Please enter a message."}), 400

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=config.SYSTEM_PROMPT,
                temperature=0.6,
            ),
        )
        reply = (response.text or "").strip()
    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

    return jsonify({"reply": reply or "I couldn't generate a response. Please try again."})


if __name__ == "__main__":
    app.run(debug=True)
