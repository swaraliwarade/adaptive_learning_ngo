import streamlit as st
from groq import Groq

# Setup Groq Client
try:
    # Looks for GROQ_API_KEY in your Streamlit Secrets
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    # Fallback for local
    client = None

def ask_ai(prompt):
    if client:
        try:
            # Using Llama-3.3-70b or Llama3-8b for high speed and accuracy
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Sahay AI, a helpful mentor for a peer-learning platform."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI Error: {str(e)}"
    
    return "AI is not configured. Please add GROQ_API_KEY to secrets."
