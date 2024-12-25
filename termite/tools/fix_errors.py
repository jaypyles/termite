# Third party
from rich.progress import Progress

# Local

try:
    from termite.dtos import Script
    from termite.shared import run_tui, call_llm, MAX_TOKENS
except ImportError:
    from dtos import Script
    from shared import run_tui, call_llm, MAX_TOKENS


#########
# HELPERS
#########


PROMPT = """You are an expert Python programmer tasked with fixing a terminal user interface (TUI) implementation.
Your goal is to analyze, debug, and rewrite a broken Python script to make the TUI work without errors.

Before providing the fixed Python script, think through the debugging process using the following steps:

<debugging_process>
1. Analyze the provided Python script and the error message.
2. Identify the issues in the script that are causing the error.
3. Rewrite the script to fix the issues and make the TUI work without errors.
4. Ensure that the TUI continues to adhere to the original TUI design document.
5. Do NOT use any try/except blocks. All exceptions must ALWAYS be raised.
6. Continue using the {library} library. Do NOT use any other TUI libraries.
</debugging_process>

Respond with the complete, fixed Python script without any explanations or markdown formatting."""


def parse_code(output: str) -> str:
    chunks = output.split("```")

    if len(chunks) == 1:
        return output

    # TODO: Do not join all chunks back together –– just get the first chunk after the delimiter
    code = "```".join(chunks[1:-1]).strip()
    if code.split("\n")[0].lower().startswith("python"):
        code = "\n".join(code.split("\n")[1:])

    return code


######
# MAIN
######


def fix_errors(
    script: Script, design: str, p_bar: Progress, max_retries: int = 10
) -> Script:
    # TODO: Use count_tokens(script.code) instead of MAX_TOKENS // 12
    progress_limit = max_retries * (MAX_TOKENS // 12)
    task = p_bar.add_task("fix", total=progress_limit)

    num_retries = 0
    curr_script = script
    while num_retries < max_retries:
        run_tui(curr_script)

        if not curr_script.stderr:
            p_bar.update(task, completed=progress_limit)
            return curr_script

        messages = [
            {"role": "user", "content": design},
            {"role": "assistant", "content": curr_script.code},
            {
                "role": "user",
                "content": f"<error>\n{curr_script.stderr}\n</error>\n\nFix the error above. Remember: you CANNOT suppress exceptions.",
            },
        ]
        output = call_llm(
            system=PROMPT.format(library="urwid"),
            messages=messages,
            stream=True,
            prediction={"type": "content", "content": curr_script.code},
        )
        code = ""
        for token in output:
            code += token
            p_bar.update(task, advance=1)
        code = parse_code(code)
        curr_script = Script(code=code)

        p_bar.update(task, advance=1)
        num_retries += 1

    p_bar.update(task, completed=progress_limit)
    return curr_script


# TODO: More granular progress
# TODO: Include the fix history in the messages
# TODO: Use self-consistency
