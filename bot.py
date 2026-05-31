import discord
import os
import re
import io
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN")

TARGET_CHANNEL = 1510294219384946919
SECOND_TARGET_CHANNEL = 1510556918853402716

class DeobfBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        await self.tree.sync()

async def run_deobf(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    matches = re.findall(r"\\(\d+)", text)
    if not matches:
        return None
    return "".join(chr(int(num)) for num in matches)

async def run_websim(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    if "q1=" in text and ("Rz=" in text or "kx=" in text or "m0d=" in text):
        hex_match = re.search(r'q1="([0-9a-f]+)"', text)
        if hex_match:
            payload = hex_match.group(1)
            bytes_data = [int(payload[i:i+2],16) for i in range(0,len(payload),2)]
            decoded = ''.join(chr(b ^ ((0xee + (i*7)) % 256)) for i,b in enumerate(bytes_data))
            return decoded
        return None
    return None

client = DeobfBot()

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id == TARGET_CHANNEL and message.content.lower().startswith(".seel"):
        await client.process_commands(message)
        return
    if message.channel.id == SECOND_TARGET_CHANNEL and message.content.lower().startswith(".websim"):
        await client.process_commands(message)
        return
    await client.process_commands(message)

@client.command(name="seel")
async def seel_prefix(ctx: commands.Context):
    try:
        if not ctx.message.attachments:
            await ctx.send("Attach only a .lua or .txt file.")
            return
        content = await ctx.message.attachments[0].read()
        result = await run_deobf(content)
        if result is None:
            await ctx.send("💀 Its not LuaSeel bro")
            return
        output = io.BytesIO(result.encode("utf-8"))
        await ctx.send(content="😂 Here is your deobfuscated script skid",
                       file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await ctx.send("😭 Deobfuscation failed.")

@client.tree.command(name="luaseel-deobf", description="Deobfuscate LuaSeel scripts")
@app_commands.describe(file="Upload your .lua or .txt file only!")
async def luaseel_deobf(interaction: discord.Interaction, file: discord.Attachment):
    try:
        content = await file.read()
        result = await run_deobf(content)
        if result is None:
            await interaction.response.send_message("💀 Its not LuaSeel bro")
            return
        output = io.BytesIO(result.encode("utf-8"))
        await interaction.response.send_message(content="😂 Here is your deobfuscated script skid",
                                                file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await interaction.response.send_message("😭 Deobfuscation failed.")

@client.command(name="websim")
async def websim_prefix(ctx: commands.Context):
    try:
        if not ctx.message.attachments:
            await ctx.send("Attach only a .lua or .txt file.")
            return
        content = await ctx.message.attachments[0].read()
        result = await run_websim(content)
        if result is None:
            await ctx.send("Its not websim lua obfuscator 💀")
            return
        output = io.BytesIO(result.encode("utf-8"))
        await ctx.send(content="Deobfuscation Success! See the result below!",
                       file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await ctx.send("😭 WebSim deobfuscation failed.")

@client.tree.command(name="websim-deobf", description="Deobfuscate script that uses websim lua obfuscator.")
@app_commands.describe(file="Upload your .lua or .txt file only!")
async def websim_deobf(interaction: discord.Interaction, file: discord.Attachment):
    try:
        content = await file.read()
        result = await run_websim(content)
        if result is None:
            await interaction.response.send_message("Its not websim lua obfuscator 💀")
            return
        output = io.BytesIO(result.encode("utf-8"))
        await interaction.response.send_message(content="Deobfuscation Success! See the result below!",
                                                file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await interaction.response.send_message("😭 WebSim deobfuscation failed.")

def handler(request):
    return {"status": "ok", "message": "Discord bot running"}

@client.event
async def on_ready():
    print(f"Bot ready as {client.user}")

client.run(TOKEN)
