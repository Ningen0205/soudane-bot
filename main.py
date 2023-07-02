import asyncio
import discord
import discord.app_commands
import html
import os
from google.cloud import texttospeech

import os
from dotenv import load_dotenv
import logging

load_dotenv()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


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


@client.event
async def on_ready():
    logging.info("Bot is ready.")
    await tree.sync()


@tree.command(name="play", description="そうだねと同意してくれます。")
async def play(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # ボイスチャンネルに接続
    voice = interaction.user.voice
    target_channel = getattr(voice, "channel", None)
    if voice is None or target_channel is None:
        await interaction.followup.send("先にボイスチャンネルに入ってください。")
        return

    if interaction.client.voice_clients:
        await interaction.followup.send("既にボイスチャンネルに接続しています。")
        return

    # 音声ファイルの再生
    voice_client = await target_channel.connect()
    source = discord.FFmpegPCMAudio("./sounds/soudane.mp3", before_options="-vol 100")

    voice_client.play(source)

    # 再生終了まで待機
    while voice_client.is_playing():
        await asyncio.sleep(0.5)

    # ボイスチャンネルから切断
    await voice_client.disconnect()
    await interaction.followup.send("Done")


@tree.command(name="voice", description="代わって発言してくれます。")
@discord.app_commands.describe(text="Text to say.")
async def voice(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=True)

    # ボイスチャンネルに接続
    voice = interaction.user.voice
    target_channel = getattr(voice, "channel", None)
    if voice is None or target_channel is None:
        await interaction.followup.send("先にボイスチャンネルに入ってください。")
        return

    if interaction.client.voice_clients:
        await interaction.followup.send("既にボイスチャンネルに接続しています。")
        return

    voice_path = "./sounds/voice.mp3"
    ssml = text_to_ssml(text=text)
    file = ssml_to_speech(ssml, voice_path, "ja-JP", texttospeech.SsmlVoiceGender.MALE)

    # 音声ファイルの再生
    voice_client = await target_channel.connect()
    source = discord.FFmpegPCMAudio(voice_path)

    voice_client.play(source)

    # 再生終了まで待機
    while voice_client.is_playing():
        await asyncio.sleep(0.5)

    os.remove(voice_path)
    # ボイスチャンネルから切断
    await voice_client.disconnect()
    await interaction.followup.send("Done")


client.run(os.environ.get("BOT_TOKEN"))
