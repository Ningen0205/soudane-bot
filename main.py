from typing import Optional
import asyncio
import discord
import discord.app_commands
import html
import os
import datetime
from google.cloud import texttospeech

import os
from dotenv import load_dotenv
import logging

load_dotenv()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# key: member_id, value: 入室時間
member_voice_invite_time = {}


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


# TODO: channelの型付け(discord.guild.GuildChannelではエラーだった)
async def notification_current_members(channel, state: discord.VoiceState):
    filtered = filter(lambda m: not m.bot, state.channel.members)
    current_member_names = list(map(lambda m: m.display_name, filtered))
    display_member_text = " ".join(current_member_names)

    if not len(current_member_names):
        return

    await channel.send(
        f"""現在の参加者
```
{display_member_text}
```
"""
    )


@client.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    # ミュートの変更の場合は、対応しない。
    if before.channel == after.channel:
        return

    # 通知メッセージを書き込むテキストチャンネル（チャンネルIDを指定）
    botRoom = client.get_channel(int(os.environ.get("VOICE_NOTIFICATION_CHANNEL_ID")))

    # 入退室を監視する対象のボイスチャンネル（チャンネルIDを指定）
    announceChannelIds = [int(os.environ.get("VOICE_MONITOR_CHANNEL_ID"))]

    # 入室通知
    if (
        after.channel is not None
        and not member.bot
        and after.channel.id in announceChannelIds
    ):
        member_voice_invite_time[member.id] = datetime.datetime.now()
        await botRoom.send(f"""**{after.channel.name}**に、__{member.name}__が参加しました!""")
        await notification_current_members(botRoom, after)
    # 退室通知
    if (
        before.channel is not None
        and not member.bot
        and before.channel.id in announceChannelIds
    ):
        invite_time: Optional[datetime.datetime] = member_voice_invite_time.get(
            member.id
        )

        if not invite_time:
            await botRoom.send(
                f"""**{before.channel.name}**から、__{member.name}__が抜けました!"""
            )
            await notification_current_members(botRoom, before)
            return

        stay_time: datetime.timedelta = datetime.datetime.now() - invite_time

        # format stay_time
        days = stay_time.days
        hours = stay_time.seconds // 3600
        minutes = (stay_time.seconds - (hours * 3600)) // 60
        seconds = stay_time.seconds - (hours * 3600 + minutes * 60)
        display_stay_time = f"""{days}日{hours}時間{minutes}分{seconds}秒"""

        await botRoom.send(
            f"""**{before.channel.name}**から、__{member.name}__が抜けました! 滞在時間: {display_stay_time}"""
        )
        await notification_current_members(botRoom, before)


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
