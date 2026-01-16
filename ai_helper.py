import streamlit as st
from openai import OpenAI

# Setup OpenAI Client
try:
    # Looks for OPENAI_API_KEY in your Streamlit Secrets
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    client = None

def ask_ai(prompt):
    if client:
        try:
            # Using gpt-3.5-turbo for speed and cost-efficiency
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Sahay AI, a helpful mentor for a peer-learning platform."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            # Common errors: Insufficient balance (402) or Invalid Key (401)
            return f"AI Error: {str(e)}"
    
    return "AI is not configured. Please add OPENAI_API_KEY to secrets."
