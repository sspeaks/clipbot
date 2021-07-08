import os

import discord
from dotenv import load_dotenv
import aiohttp
import json
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GIPHY_API_KEY = os.getenv('GIPHY_API_KEY')

client = discord.Client()

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

@client.event
async def on_message(message):
    print(message.channel.name)
    if message.author == client.user:
        return
    if message.channel.name != 'pogcheck':
        return
    if message.content == '!pogcheck':
        embed = discord.Embed(colour=discord.Colour.blue())
        session = aiohttp.ClientSession()

        response = await session.get(f'http://api.giphy.com/v1/gifs/random?tag=pog&api_key={GIPHY_API_KEY}')
        print(response.text())
        data = json.loads(await response.text())
        embed.set_image(url=data['data']['images']['original']['url'])
        await session.close()

        pog_choice = random.randint(1,10)
        msg = get_random_message(pog_choice)
        await message.channel.send(msg, embed=embed)

def get_random_message(val):
    low_rating = [f"Uh bro, you thought that was pog? It’s only a {val} on the pogmeter!",
                    f"Seriously bro that’s so unpog! It’s a {val} on the pogmeter!",
                    f"Okay bro, you can pretend that was pog but its just a {val} on the pogmeter…"]

    medium_rating = [f"Alright bro, I’ll give it to you that’s a {val} on the pogmeter",
                f"Gotta say that’s pretty sweet bro, it’s a {val} on the pogmeter.",
                f"Woah bro, that’s a {val} on the pogmeter!"]


    high_rating = [f"I never thought anything could be as pog as Chin…but that’s a {val} on the pogmeter!",
            f"Dude…that’s more pog than Bluffkin…its a {val} on the pogmeter!",
            f"Bro, seriously that’s the most poggiest thing ever! Its a {val} on the pogmeter!"]


    multi_rating = [f"Bro, can you believe that’s like a {val} on the pogmeter?!",
                f"Bro listen! That’s definitely a {val} on the pogmeter.",
                f"Alright bro, hear me out. That has got to be a {val} on the pogmeter."]

    chosen_list = low_rating if val <= 4 else medium_rating if val > 4 and val < 7 else high_rating
    chosen_list = chosen_list + multi_rating
    return random.choice(chosen_list)


client.run(TOKEN)
#! /usr/bin/env nix-shell
#! nmeix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp

