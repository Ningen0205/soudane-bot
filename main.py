import asyncio
import discord
from discord.ext import commands

import os
from dotenv import load_dotenv


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("Bot is ready.")


@bot.command()
async def play(ctx):
    # ボイスチャンネルに接続
    channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is not None and voice_client.is_connected():
        await ctx.send("既にボイスチャンネルに接続しています。")
        return

    # 音声ファイルの再生
    voice_client = await channel.connect()
    source = discord.FFmpegPCMAudio("./sounds/soudane.mp3", before_options="-vol 100")

    voice_client.play(source)

    # 再生終了まで待機
    while voice_client.is_playing():
        await asyncio.sleep(0.5)

    # ボイスチャンネルから切断
    await voice_client.disconnect()


bot.run(os.environ.get("BOT_TOKEN"))
