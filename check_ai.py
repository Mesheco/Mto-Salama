"""
Phase 0 - Day 1 check: can we call the Claude API?

Run:  python check_ai.py
Cost: one tiny call on Claude Haiku 5.5, a fraction of a US cent.
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("MTO_MODEL", "anthropic/claude-haiku-5-5").split("/")[-1]

if not api_key or api_key == "paste_your_key_here":
    raise SystemExit("No Claude key found. Create a .env file from .env.example first.")
if model == "mockllm":
    raise SystemExit("MTO_MODEL is set to mockllm (offline demo). Set it to "
                     "anthropic/claude-haiku-5-5 to test the real API.")

client = anthropic.Anthropic(api_key=api_key)

reply = client.messages.create(
    model=model,
    max_tokens=200,
    system="You write short, calm river safety alerts. Never say a crossing is guaranteed safe.",
    messages=[
        {"role": "user", "content": "Write a 2-line alert in Swahili and English: heavy rain "
                                    "fell upstream, people should not cross the drift today. "
                                    "End with: emergencies call 1199."},
    ],
)

print(f"Model: {model}\n")
print(reply.content[0].text)
print(f"\nTokens used - input: {reply.usage.input_tokens}, output: {reply.usage.output_tokens}")
