import os

from pogbot.config import CLIENT, TOKEN, GUILD
from pogbot.clipping.web.server import start_web_server
from pogbot.clipping.detector import run_temp_cleanup

# Importing commands registers the @CLIENT.event handlers
import pogbot.commands  # noqa: F401

WEB_PORT = int(os.getenv("POGBOT_WEB_PORT", "8080"))


@CLIENT.event
async def on_connect():
    print("CONNECTED!")
    print(CLIENT.guilds)


@CLIENT.event
async def on_ready():
    for guild in CLIENT.guilds:
        if guild.name == GUILD:
            print(
                f"{CLIENT.user} is connected to the following guild:\n"
                f"{guild.name}(id: {guild.id})"
            )
            break


@CLIENT.event
async def setup_hook():
    await start_web_server(port=WEB_PORT)
    CLIENT.loop.create_task(run_temp_cleanup())


CLIENT.run(TOKEN)

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp python38Packages.pynacl ffmpeg
