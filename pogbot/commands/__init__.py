import re

from pogbot.config import CLIENT
from pogbot.storage import get_updated_tokens_for_user
from pogbot.commands.audio import (
    play_pog_file,
    play_file,
    process_get_files,
    process_tokens_command,
    start_listening,
    stop_listening,
)
from pogbot.commands.fun import (
    handle_pogcheck_message,
    process_better_mage,
    print_help_message,
)
from pogbot.commands.ai import process_chat_command, process_image_command


COMMANDS = {
    "!pogcheck": lambda msg: handle_pogcheck_message(msg),
    "!pogmedaddy": lambda msg: play_pog_file(msg),
    "!help": lambda msg: print_help_message(msg),
    "!bettermage": lambda msg: process_better_mage(msg),
    "!playclip": lambda msg: play_file(msg, get_updated_tokens_for_user(msg.author)),
    "!tokens": lambda msg: process_tokens_command(msg, get_updated_tokens_for_user(msg.author)),
    "!chat": lambda msg: process_chat_command(msg),
    "!image": lambda msg: process_image_command(msg),
    "!listen": lambda msg: start_listening(msg),
    "!leave": lambda msg: stop_listening(msg),
}


@CLIENT.event
async def on_message(message):
    if message.author == CLIENT.user:
        return

    if re.search("pog", message.content, flags=re.IGNORECASE):
        await message.add_reaction("<:mentos:1044740202947678228>")

    # !files only works in DMs
    if message.content == "!files" and re.search("^Direct Message", str(message.channel)):
        await process_get_files(message)
        return

    # Channel-restricted commands
    command = message.content.split()[0] if message.content else ""
    if command in COMMANDS:
        if command in ("!image",) or str(message.channel) == "poggers":
            await COMMANDS[command](message)
