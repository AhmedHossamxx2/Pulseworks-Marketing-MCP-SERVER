import asyncio
import os
import sys
import time
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_core import run_agent_query

# ======================================================
# ANSI Colors
# ======================================================
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

MAX_HISTORY = 10


async def chat_loop():
    print(f"{YELLOW}======================================================{RESET}")
    print(f"{GREEN}🚀 AI Marketing & Analytics Agent - Local CLI 🚀{RESET}")
    print(f"{YELLOW}Type 'exit' or 'quit' to stop the session.{RESET}")
    print(f"{YELLOW}======================================================{RESET}\n")

    chat_history: List[BaseMessage] = []

    while True:
        try:
            user_input = input(f"{BLUE}You:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Exiting gracefully...{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ['exit', 'quit']:
            print(f"{YELLOW}Goodbye! 👋{RESET}")
            break

        print(f"{YELLOW}Agent is thinking... ⏳{RESET}")

        start_time = time.time()

        result = await run_agent_query(
            user_input=user_input,
            chat_history=chat_history,
            ctx=None  # CLI mode (no MCP yet)
        )

        elapsed = time.time() - start_time

        # ==================================================
        # SUCCESS
        # ==================================================
        if result["status"] == "success":
            
            raw_output = result["output"]

            # ✅ تنظيف شكل الرد (التعديل الوحيد)
            if isinstance(raw_output, list):
                output = "\n".join(
                    item.get("text", "")
                    for item in raw_output
                    if isinstance(item, dict)
                )
            else:
                output = raw_output

            steps = result.get("intermediate_steps", [])

            # --- Tool Debug (FIXED) ---
            if steps:
                print(f"\n{YELLOW}--- 🛠️ Tools Triggered ---{RESET}")

                for step in steps:
                    tool_name = "unknown"
                    tool_input = {}

                    try:
                        if isinstance(step, tuple) and len(step) == 2:
                            action, observation = step

                            tool_name = getattr(action, "tool", None) \
                                        or getattr(action, "name", None) \
                                        or "unknown"

                            tool_input = getattr(action, "tool_input", None) \
                                         or getattr(action, "args", None) \
                                         or {}

                        elif isinstance(step, dict):
                            tool_name = step.get("tool") \
                                        or step.get("name") \
                                        or "unknown"

                            tool_input = step.get("args") \
                                         or step.get("tool_input") \
                                         or {}

                        else:
                            tool_name = getattr(step, "tool", None) \
                                        or getattr(step, "name", None) \
                                        or "unknown"

                            tool_input = getattr(step, "tool_input", None) \
                                         or getattr(step, "args", None) \
                                         or {}

                    except Exception as e:
                        print(f"{RED}Error reading step: {e}{RESET}")

                    print(f"🔹 {YELLOW}Tool:{RESET} {tool_name}")
                    print(f"🔹 {YELLOW}Args:{RESET} {tool_input}")

                print(f"{YELLOW}--------------------------{RESET}\n")

            else:
                print(f"{YELLOW}(No tools used — direct LLM response){RESET}\n")

            # --- Output ---
            print(f"{GREEN}Agent:{RESET} {output}")
            print(f"{YELLOW}⏱️ Took: {elapsed:.2f}s{RESET}\n")

            # --- Update Memory ---
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=output))

        # ==================================================
        # ERROR
        # ==================================================
        else:
            print(f"\n{RED}❌ Error:{RESET} {result['output']}")

            if "traceback" in result:
                print(f"{RED}{result['traceback']}{RESET}\n")

            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=result["output"]))

        # --- Trim Memory ---
        if len(chat_history) > MAX_HISTORY * 2:
            chat_history = chat_history[-MAX_HISTORY * 2:]


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nSession terminated.")