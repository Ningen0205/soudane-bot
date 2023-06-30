import asyncio
import discord
from discord.ext import commands
import html
import os
from google.cloud import texttospeech

import os
from dotenv import load_dotenv


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

client = texttospeech.TextToSpeechClient()


def text_to_ssml(text):
    escaped_lines = html.escape(text)
    ssml = "{}".format(escaped_lines.replace("\n", '\n<break time="1s"/>'))
    return ssml


def ssml_to_speech(ssml, file, language_code, gender):
    ttsClient = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=ssml)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code, ssml_gender=gender
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = ttsClient.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(file, "wb") as out:
        out.write(response.audio_content)
    return file


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


@bot.command()
async def voice(ctx, text=None):
    if text is None:
        await ctx.send("引数に指定してね")
        return

    channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is not None and voice_client.is_connected():
        await ctx.send("既にボイスチャンネルに接続しています。")
        return

    voice_path = "./sounds/voice.mp3"
    ssml = text_to_ssml(text=text)
    file = ssml_to_speech(ssml, voice_path, "ja-JP", texttospeech.SsmlVoiceGender.MALE)

    # 音声ファイルの再生
    voice_client = await channel.connect()
    source = discord.FFmpegPCMAudio(voice_path)

    voice_client.play(source)

    # 再生終了まで待機
    while voice_client.is_playing():
        await asyncio.sleep(0.5)

    # ボイスチャンネルから切断
    await voice_client.disconnect()
    os.remove(voice_path)


bot.run(os.environ.get("BOT_TOKEN"))
