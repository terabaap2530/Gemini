from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__, template_folder="templates")  # Ensure 'templates' folder is used

# ðŸ”¹ Gemini API Key (Yahan Direct Enter Kiya Gaya Hai)
GEMINI_API_KEY = "AIzaSyD2q5Rnk8bnHL1FIPT3FTkTYKAVps_f0FM"

# ðŸ”¹ Gemini API Call Function
def get_gemini_response(user_input):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [
            {
                "parts": [{"text": user_input}]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, params=params)
    
    if response.status_code == 200:
        return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
    else:
        return f"Error: {response.json()}"

# ðŸ”¹ Home Route (Serve HTML Page)
@app.route("/")
def home():
    return render_template("index.html")  # Ensure 'index.html' exists in 'templates/' folder

# ðŸ”¹ API Route
@app.route("/chat", methods=["GET"])
def chat():
    user_message = request.args.get("message")
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    response_text = get_gemini_response(user_message)
    
    return jsonify({"reply": response_text})

# ðŸ”¹ Server Run Karne Ke Liye
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
