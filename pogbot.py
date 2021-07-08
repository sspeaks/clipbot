
import os
import json
import random
import discord
from dotenv import load_dotenv
import aiohttp


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GIPHY_API_KEY = os.getenv('GIPHY_API_KEY')

CLIENT = discord.Client()


@CLIENT.event
async def on_ready():
    for guild in CLIENT.guilds:
        if guild.name == GUILD:
            print(
                f'{CLIENT.user} is connected to the following guild:\n'
                f'{guild.name}(id: {guild.id})'
            )
            break


@CLIENT.event
async def on_message(message):
    if should_process_message(message):
        pog_choice = random.randint(1, 10)
        msg = get_random_message(pog_choice)
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_image(url=await get_random_image_url('pog', 'lame', pog_choice))
        await message.channel.send(msg, embed=embed)

async def get_random_image_url(high_word, low_word, score):
    session = aiohttp.ClientSession()
    keyword = high_word if score > 5 else low_word
    response = await session.get(f'http://api.giphy.com/v1/gifs/random?tag={keyword}&api_key={GIPHY_API_KEY}')
    data = json.loads(await response.text())
    await session.close()
    return data['data']['images']['original']['url']

def should_process_message(message):
    if message.author == CLIENT.user:
        return False
    if message.channel.name != 'pogcheck':
        return False
    if message.content == '!pogcheck':
        return True
    return False

def get_random_message(val):
    low_rating = [
        f"Uh bro, you thought that was pog? It’s only a {val} on the pogmeter!",
        f"Seriously bro that’s so unpog! It’s a {val} on the pogmeter!",
        f"Okay bro, you can pretend that was pog but its just a {val} on the pogmeter…"
        ]

    medium_rating = [
        f"Alright bro, I’ll give it to you that’s a {val} on the pogmeter",
        f"Gotta say that’s pretty sweet bro, it’s a {val} on the pogmeter.",
        f"Woah bro, that’s a {val} on the pogmeter!"
        ]


    high_rating = [
        f"I never thought anything could be as pog as Chin…but that’s a {val} on the pogmeter!",
        f"Dude…that’s more pog than Bluffkin…its a {val} on the pogmeter!",
        f"Bro, seriously that’s the most poggiest thing ever! Its a {val} on the pogmeter!"
        ]


    multi_rating = [
        f"Bro, can you believe that’s like a {val} on the pogmeter?!",
        f"Bro listen! That’s definitely a {val} on the pogmeter.",
        f"Alright bro, hear me out. That has got to be a {val} on the pogmeter."
        ]

    chosen_list = low_rating if val <= 4 else medium_rating if 4 < val < 7 else high_rating
    chosen_list += multi_rating
    return random.choice(chosen_list)


CLIENT.run(TOKEN)
#! /usr/bin/env nix-shell
#! nmeix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp
