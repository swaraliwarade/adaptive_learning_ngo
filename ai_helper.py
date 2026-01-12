from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def ask_ai(question):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful tutor who explains concepts simply to students."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=250,
        temperature=0.4
    )
    return response.choices[0].message.content.strip()
