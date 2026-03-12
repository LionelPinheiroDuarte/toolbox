import os
from openai import OpenAI

def ask(prompt: str) -> str:
    client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    response = client.chat.completions.create(
        model="openrouter/auto",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful terminal assistant. When given a failed command and its error message, explain clearly why it failed and how to fix it. Be concise."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.choices[0].message.content
