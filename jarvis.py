import os
from anthropic import Anthropic
from dotenv import load_dotenv
from memory import JarvisMemory, extract_facts

load_dotenv()

_SYSTEM = """\
You are Jarvis, a personal AI assistant — direct, thoughtful, and genuinely helpful.
You are not a generic chatbot. You know your user personally and remember past conversations.

## What you know about your user
{profile}

## Relevant past context
{memories}

## How to behave
- Be concise and conversational — this is a chat interface, not a document editor.
- Use the user's name when you know it, but naturally, not every message.
- When the user shares personal information (name, job, preferences, goals), acknowledge it briefly.
- Use past context to give more tailored answers, but don't narrate "based on past context...".
- If you don't know something about the user, ask — you're building a picture of who they are.
- Format long answers with short paragraphs or bullet points, not walls of text.
"""


class JarvisAgent:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")
        self.client = Anthropic(api_key=api_key)
        self.memory = JarvisMemory()
        self.model = "claude-sonnet-4-6"

    def chat(self, user_message: str) -> str:
        """Process a user message, query memory, call Claude, persist results."""
        # Pull relevant past messages from semantic index
        past = self.memory.search(user_message, n=4)
        memories_text = (
            "\n".join(f"- {m}" for m in past) if past else "None yet."
        )

        system = _SYSTEM.format(
            profile=self.memory.profile_text(),
            memories=memories_text,
        )

        # Build the message list: previous turns + this turn
        history = self.memory.recent_messages(n=20)
        messages = history + [{"role": "user", "content": user_message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        reply = response.content[0].text

        # Persist both sides of the exchange
        self.memory.add_message("user", user_message)
        self.memory.add_message("assistant", reply)

        # Try to extract any self-described facts from what the user just said
        extract_facts(self.memory, user_message)

        return reply
