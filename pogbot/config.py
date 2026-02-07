import os

import discord
import openai

print(os.environ["LD_LIBRARY_PATH"])
os.environ["LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]

dir_path = open(os.getenv("ASSETS_PATH"), "r").read()
TOKEN = open(os.getenv("DISCORD_TOKEN"), "r").read()
GUILD = os.getenv("DISCORD_GUILD")
GIPHY_API_KEY = open(os.getenv("GIPHY_API_KEY"), "r").read()
OPEN_AI_API = open(os.getenv("OPEN_AI_KEY"), "r").read()

openai.api_key = OPEN_AI_API

intents = discord.Intents.default()
intents.message_content = True
CLIENT = discord.Client(intents=intents)
discord.opus.load_opus("libopus.so")
