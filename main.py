import random
from typing import Optional
from datetime import datetime, date
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


# 1日
SOUDANE_THREADHOLD = 5
# key が日付, valueが誰が読んだかの配列
SOUNDANE_MEMORY_DB = {}


class ThreadHoldException(Exception):
    pass


class SoudaneRepository:
    SOUDANE_FILE_NAMES = [
        "./sounds/soudane.mp3",
        "./sounds/soudane_tiru_1.mp3"
    ]
    @classmethod
    def get_soudane_file_name(cls):
        return cls.SOUDANE_FILE_NAMES[random.randint(0, len(cls.SOUDANE_FILE_NAMES) - 1)]
        

    @classmethod
    def get(cls, date_: date):
        return SOUNDANE_MEMORY_DB.get(str(date_))

    @classmethod
    def save(cls, date_: date, user: discord.User):
        key = str(date_)
        called_list = SOUNDANE_MEMORY_DB.get(str(date_))  # type: Optional[list] 
        if called_list is None:
            SOUNDANE_MEMORY_DB[key] = [user.display_name]
        elif len(called_list) < SOUDANE_THREADHOLD:
            SOUNDANE_MEMORY_DB[key].append(user.display_name)
        else:
            raise ThreadHoldException()


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

    target_channel = client.get_channel(int(os.environ.get("DEFAULT_VOICE_CHANNEL_ID")))
    if interaction.client.voice_clients:
        await interaction.followup.send("既にボイスチャンネルに接続しています。")
        return

    try:
        SoudaneRepository.save(date_=datetime.now().date(), user=interaction.user)
    except ThreadHoldException:
        called_members = SoudaneRepository.get(date_=datetime.now().date())
        display_text = "\n".join(called_members)
        notification_channel = client.get_channel(
            int(os.environ.get("NOTIFICATION_CHANNEL_ID"))
        )
        await interaction.followup.send("Done")
        await notification_channel.send(
            f"""本日の呼び出し回数を超過しました。
呼び出し情報:
```
{display_text}
```                                 
"""
        )
        return

    # 音声ファイルの再生
    voice_client = await target_channel.connect()
    source = discord.FFmpegPCMAudio(SoudaneRepository.get_soudane_file_name(), before_options="-vol 100")

    voice_client.play(source)

    # 再生終了まで待機
    while voice_client.is_playing():
        await asyncio.sleep(0.5)

    # ボイスチャンネルから切断
    await voice_client.disconnect()
    await interaction.followup.send("Done")

    logging.info(
        "called soudane api.",
        extra={
            "user": {"id": interaction.user.id, "name": interaction.user.name},
        },
    )


@tree.command(name="voice", description="代わって発言してくれます。")
@discord.app_commands.describe(text="Text to say.")
async def voice(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=True)

    target_channel = client.get_channel(int(os.environ.get("DEFAULT_VOICE_CHANNEL_ID")))
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

    notification_channel = client.get_channel(
        int(os.environ.get("NOTIFICATION_CHANNEL_ID"))
    )
    await notification_channel.send(f"{interaction.user.name}が「{text}」と命令しました。")
    logging.info(
        "called voice api.",
        extra={
            "user": {"id": interaction.user.id, "name": interaction.user.name},
            "text": text,
        },
    )


client.run(os.environ.get("BOT_TOKEN"))
