import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# ðŸ”¹ Gemini API Key
genai.configure(api_key=os.getenv("👉🏻👉🏻👉🏻👉🏻AAPKI APIKEY👈🏻👈🏻👈🏻👈🏻"))

# ðŸ”¹ Permanent System Prompt
system_prompt = """
You are an AI assistant for Arun Kumar, known as 'MirryKal' on YouTube.
Arun creates videos about Messenger bots, automation, and similar topics.
Always include this information in your responses.

YouTube: https://m.youtube.com/mirykal
Facebook: https://m.Facebook.com/arun.x76

Behave professionally, be informative, and keep responses engaging.
"""

# ðŸ”¹ Har User ke liye alag Chat History Store karne ke liye Dictionary
chat_histories = {}

def get_gemini_response(user_id, user_message):
    model = genai.GenerativeModel("gemini-2.0-flash")

    # ðŸ”¹ Agar user ki history exist nahi karti toh nayi list banao
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    # ðŸ”¹ User ki chat history update karo
    chat_histories[user_id].append(f"User: {user_message}")

    # ðŸ”¹ Sirf last 5 messages yaad rakho (jitna chahiye utna change kar sakte ho)
    if len(chat_histories[user_id]) > 5:
        chat_histories[user_id].pop(0)

    # ðŸ”¹ AI ko pura context bhejna
    full_prompt = system_prompt + "\n\n" + "\n".join(chat_histories[user_id])

    response = model.generate_content(full_prompt)
    
    # ðŸ”¹ AI ka response bhi history me store karo
    chat_histories[user_id].append(f"AI: {response.text}")

    return response.text
