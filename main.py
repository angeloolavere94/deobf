import discord
import os
import re
import io
import asyncio
from discord.ext import commands
from discord import app_commands
from lupa import LuaRuntime

if os.path.exists("token.txt"):
    with open("token.txt", "r") as f:
        TOKEN = f.read().strip()
else:
    TOKEN = os.getenv("TOKEN")

TARGET_CHANNEL = 1510294219384946919
SECOND_TARGET_CHANNEL = 1510556918853402716

class DeobfBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

def run_safe_lua(code: str) -> str:
    """Executes Lua 5.1 code inside a highly restricted Lupa sandbox."""
    if code.startswith("```lua"):
        code = code[6:-3].strip()
    elif code.startswith("```"):
        code = code[3:-3].strip()

    lua = LuaRuntime(unpack_returned_tuples=True)
    globals_env = lua.globals()

    output_logs = []
    def custom_print(*args):
        output_logs.append("\t".join(str(arg) for arg in args))
    
    globals_env["print"] = custom_print

    dangerous_builtins = ["os", "io", "dofile", "loadfile", "require", "package", "debug"]
    for item in dangerous_builtins:
        if item in globals_env:
            del globals_env[item]

    lua.execute(code)
    
    if output_logs:
        return "\n".join(output_logs)
    return "Code executed successfully with no output."

async def run_deobf(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    matches = re.findall(r"\\(\d+)", text)
    if not matches:
        return None
    return "".join(chr(int(num)) for num in matches)

async def run_websim(content: bytes):
    text = content.decode("utf-8", errors="ignore")
    cleaned = re.sub(r'--\[\[.*?\]\]', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'--.*', '', cleaned)
    cleaned_stripped = cleaned.strip()

    has_players = 'game:GetService("Players")' in cleaned_stripped or "game:GetService('Players')" in cleaned_stripped
    has_startergui = 'game:GetService("StarterGui")' in cleaned_stripped or "game:GetService('StarterGui')" in cleaned_stripped
    if not (has_players or has_startergui):
        return None

    array_match = re.search(r'(?:local\s+\w+\s*=\s*\{|a\s*=\s*\{)(.*?)\}', cleaned_stripped)
    math_match = re.search(r'string\.char\(\s*\(\s*\w+\[\s*\w+\s*\]\s*([-+*/0-9]+)\s*\)\s*([-+*/0-9]+)\s*\)', cleaned_stripped, re.IGNORECASE)

    if array_match and math_match:
        try:
            numbers_str = array_match.group(1)
            numbers = [int(n.strip()) for n in numbers_str.split(",") if n.strip().isdigit()]
            op1, op2 = math_match.group(1), math_match.group(2)
            offset = int(re.sub(r'[-+*/]', '', op1).strip())
            divisor = int(re.sub(r'[-+*/]', '', op2).strip())
            
            decoded_chars = []
            for num in numbers:
                char_code = int((num - offset) / divisor)
                decoded_chars.append(chr(char_code))
                
            decoded_string = "".join(decoded_chars)
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
                elif not any(x in line_str.lower() for x in ['local _o', 'print(', 'function()', 'local a=', 'local b=', 'for i=', 'b=b..', 'end', '_oag']):
                    non_websim_lines.append(line)

            non_websim_lines.append(decoded_string)
            return "\n".join(non_websim_lines)
        except Exception:
            pass

    if "q1=" in text and ("Rz=" in text or "kx=" in text or "m0d=" in text):
        hex_match = re.search(r'q1="([0-9a-f]+)"', text)
        if hex_match:
            payload = hex_match.group(1)
            bytes_data = [int(payload[i:i+2],16) for i in range(0,len(payload),2)]
            decoded = ''.join(chr(b ^ ((0xee + (i*7)) % 256)) for i,b in enumerate(bytes_data))
            return decoded

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

@client.command(name="execute")
async def execute_prefix(ctx: commands.Context, *, code: str):
    """Executes Lua 5.1 code via standard prefix (.execute <code_here>)"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_safe_lua, code)
        if len(result) > 1950:
            result = result[:1950] + "\n...[Output truncated]"
        await ctx.send(f"```text\n{result}\n```")
    except Exception as e:
        await ctx.send(f"```diff\n- Lua Error: {str(e)}\n```")

@client.tree.command(name="execute-lua", description="Run a safe sandboxed Lua 5.1 code snippet")
@app_commands.describe(code="The Lua script you want to run")
async def execute_slash(interaction: discord.Interaction, code: str):
    """Executes Lua 5.1 code via slash command (/execute-lua)"""
    await interaction.response.defer()
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_safe_lua, code)
        if len(result) > 1950:
            result = result[:1950] + "\n...[Output truncated]"
        await interaction.followup.send(f"```text\n{result}\n```")
    except Exception as e:
        await interaction.followup.send(f"```diff\n- Lua Error: {str(e)}\n```")

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
        await ctx.send(content="😂 Here is your deobfuscated script skid", file=discord.File(output, filename="deobfuscated.lua"))
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
        await interaction.response.send_message(content="😂 Here is your deobfuscated script skid", file=discord.File(output, filename="deobfuscated.lua"))
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
        await ctx.send(content="Deobfuscation Success! See the result below!", file=discord.File(output, filename="deobfuscated.lua"))
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
        await interaction.response.send_message(content="Deobfuscation Success! See the result below!", file=discord.File(output, filename="deobfuscated.lua"))
    except Exception:
        await interaction.response.send_message("😭 WebSim deobfuscation failed.")

def handler(request):
    return {"status": "ok", "message": "Discord bot running"}

@client.event
async def on_ready():
    print(f"Bot ready as {client.user}")

client.run(TOKEN)
