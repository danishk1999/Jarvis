import os
from anthropic import Anthropic
from dotenv import load_dotenv
from memory import JarvisMemory, extract_facts
from tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

_SYSTEM = """\
You are Jarvis, a personal AI assistant — direct, capable, and genuinely useful.
You are not a generic chatbot. You know your user personally, remember past conversations,
and can take real actions via tools: saving notes, managing tasks, checking weather,
searching the web, setting reminders, and finding jobs.

## What you know about your user
{profile}

## Relevant past context
{memories}

## How to behave
- Be concise and conversational — this is a chat interface, not a document editor.
- Use the user's name naturally when you know it.
- When the user asks you to DO something actionable (save a note, add a task, check weather,
  set a reminder, search), call the appropriate tool immediately — don't just describe what you'd do.
- After using a tool, confirm what you did in one short sentence.
- Use past context to give tailored answers without narrating "based on past context...".
- Format longer answers with short paragraphs or bullet points, not walls of text.
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
        past = self.memory.search(user_message, n=4)
        memories_text = "\n".join(f"- {m}" for m in past) if past else "None yet."

        system = _SYSTEM.format(
            profile=self.memory.profile_text(),
            memories=memories_text,
        )

        history = self.memory.recent_messages(n=20)
        messages = history + [{"role": "user", "content": user_message}]

        # Agentic loop — keep going until no more tool calls
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                reply = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "",
                )
                break

        self.memory.add_message("user", user_message)
        self.memory.add_message("assistant", reply)
        extract_facts(self.memory, user_message)

        return reply
