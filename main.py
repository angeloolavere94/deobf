import discord
import os
import re
import io
import aiohttp
from discord.ext import commands
from discord import app_commands

if os.path.exists("token.txt"):
    with open("token.txt", "r") as f:
        TOKEN = f.read().strip()
else:
    TOKEN = os.getenv("TOKEN")

TARGET_CHANNEL = 1510294219384946919
SECOND_TARGET_CHANNEL = 1510556918853402716

HEADER_TEXT = "-- This file was generated in Lua Land Hub | .gg/Zame2JAGDr\n\n"

class DeobfBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

async def run_deobf(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    matches = re.findall(r"\\(\d+)", text)
    if not matches:
        return None
    return HEADER_TEXT + "".join(chr(int(num)) for num in matches)

async def run_websim(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    
    cleaned = re.sub(r'--\[\[.*?\]\]', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'--.*', '', cleaned)
    cleaned_stripped = cleaned.strip()

    has_players = 'game:GetService("Players")' in cleaned_stripped or "game:GetService('Players')" in cleaned_stripped
    has_startergui = 'game:GetService("StarterGui")' in cleaned_stripped or "game:GetService('StarterGui')" in cleaned_stripped
    
    if not (has_players and has_startergui):
        return None

    array_matches = re.findall(r'(?:local\s+\w+\s*=\s*\{|\b[a-zA-Z_]\w*\s*=\s*\{)(.*?)\}', cleaned_stripped)
    math_matches = re.findall(r'string\.char\(\s*\(\s*\w+\[\s*\w+\s*\]\s*([-+*/0-9]+)\s*\)\s*([-+*/0-9]+)\s*\)', cleaned_stripped, re.IGNORECASE)

    if array_matches and math_matches:
        try:
            decoded_strings = []
            for array_str, (op1, op2) in zip(array_matches, math_matches):
                numbers = [int(n.strip()) for n in array_str.split(",") if n.strip().isdigit()]
                offset = int(re.sub(r'[-+*/]', '', op1).strip())
                divisor = int(re.sub(r'[-+*/]', '', op2).strip())
                
                decoded_chars = []
                for num in numbers:
                    char_code = int((num - offset) / divisor)
                    decoded_chars.append(chr(char_code))
                decoded_strings.append("".join(decoded_chars))
            
            lines = text.splitlines()
            non_websim_lines = []
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if 'game:GetService("Players")' in line or "game:GetService('Players')" in line:
                    non_websim_lines.append(line)
                elif 'game:GetService("StarterGui")' in line or "game:GetService('StarterGui')" in line:
                    non_websim_lines.append(line)
                elif not any(x in line_str.lower() for x in ['local _', 'print(', 'function()', 'local a=', 'local b=', 'for i=', 'b=b..', 'end', 'loadstring', 'game:httpget']):
                    non_websim_lines.append(line)

            for ds in decoded_strings:
                if ds.strip():
                    non_websim_lines.append(ds)
            return HEADER_TEXT + "\n".join(non_websim_lines)
        except Exception:
            pass

    if "q1=" in text and ("Rz=" in text or "kx=" in text or "m0d=" in text):
        hex_match = re.search(r'q1="([0-9a-f]+)"', text)
        if hex_match:
            payload = hex_match.group(1)
            bytes_data = [int(payload[i:i+2], 16) for i in range(0, len(payload), 2)]
            decoded = ''.join(chr(b ^ ((0xee + (i * 7)) % 256)) for i, b in enumerate(bytes_data))
            return HEADER_TEXT + decoded

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
            await ctx.send("💀 This is not websim bro")
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
            await interaction.response.send_message("💀 This is not websim bro")
            return
        output = io.BytesIO(result.encode("utf-8"))
        await interaction.response.send_message(content="Deobfuscation Success! See the result below!",
                                                file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await interaction.response.send_message("😭 WebSim deobfuscation failed.")

@client.tree.command(name="lua-obfuscator-deobfuscate", description="Deobfuscate an script that uses LuaObfuscator (FERIB).")
@app_commands.describe(file="Attach a .lua and .txt file only.")
async def lua_obfuscator_deobfuscate(interaction: discord.Interaction, file: discord.Attachment):
    if not (file.filename.endswith(".lua") or file.filename.endswith(".txt")):
        await interaction.response.send_message("❌ Invalid file format! Please upload only `.lua` or `.txt` files.", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        content = await file.read()
        script_text = content.decode("utf-8", errors="ignore")
        
        base_url = "https://luaobfuscator.com"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        all_modes = [
            "beautify", "minimal", "step", "strings", "constants", 
            "remove_dead_code", "inline_variables", "control_flow", 
            "un-minify", "reformat", "devirtualize", "decompile", 
            "decrypt_strings", "clean_structures"
        ]
        
        files_to_send = []

        async with aiohttp.ClientSession() as session:
            for mode in all_modes:
                payload = {
                    "script": script_text,
                    "options": {
                        "mode": mode
                    }
                }
                
                try:
                    async with session.post(base_url, json=payload, headers=headers, timeout=12) as response:
                        if response.status == 200:
                            data = await response.json()
                            deobfuscated_code = data.get("code") or data.get("result") or data.get("script")
                            
                            if deobfuscated_code and deobfuscated_code.strip() and deobfuscated_code.strip() != script_text.strip():
                                formatted_code = HEADER_TEXT + deobfuscated_code
                                output_file = io.BytesIO(formatted_code.encode("utf-8"))
                                files_to_send.append(discord.File(output_file, filename=f"deobf_{mode}.lua"))
                except Exception:
                    continue

        if not files_to_send:
            await interaction.followup.send("💀 This script doesn't seem to be a Ferib LuaObfuscator script or it cannot be parsed by any mode.")
            return

        await interaction.followup.send(content="🎉 Deobfuscation complete! Here is the actual code extracted from every matching mode:")
        for i in range(0, len(files_to_send), 10):
            chunk = files_to_send[i:i+10]
            await interaction.channel.send(files=chunk)
            
    except Exception as e:
        print(f"Error during LuaObfuscator request: {e}")
        await interaction.followup.send("😭 An unexpected framework error happened during the API extraction.")

def handler(request):
    return {"status": "ok", "message": "Discord bot running"}

@client.event
async def on_ready():
    print(f"Bot ready as {client.user}")

client.run(TOKEN)
