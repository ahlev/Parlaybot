import discord
from discord.ext import commands, tasks
import json
import asyncio

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable privileged intents for members
bot = commands.Bot(command_prefix='/', intents=intents)

nfl_picks = {}
cfb_picks = {}
admin_id = None  # Placeholder for the dedicated admin user ID

snarky_response = "Good luck with that one, you're gonna need it!"

# Load picks from file on startup
def load_picks():
    global nfl_picks, cfb_picks
    try:
        with open('nfl_picks.json', 'r') as f:
            nfl_picks = json.load(f)
    except FileNotFoundError:
        nfl_picks = {}

    try:
        with open('cfb_picks.json', 'r') as f:
            cfb_picks = json.load(f)
    except FileNotFoundError:
        cfb_picks = {}

# Save picks to file
def save_picks():
    with open('nfl_picks.json', 'w') as f:
        json.dump(nfl_picks, f)
    with open('cfb_picks.json', 'w') as f:
        json.dump(cfb_picks, f)

@bot.event
async def on_ready():
    load_picks()
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='addpick')
async def add_pick(ctx, league: str, *, pick):
    user_id = str(ctx.author.id)
    picks = nfl_picks if league.lower() == 'nfl' else cfb_picks
    if user_id in picks:
        await ctx.send(f"You already have a {league.upper()} pick for this week. Use `/editpick` to change it. \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        picks[user_id] = pick
        save_picks()
        await ctx.send(f"{league.upper()} pick added: {pick}. {snarky_response} \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

@bot.command(name='editpick')
async def edit_pick(ctx, league: str, *, new_pick):
    user_id = str(ctx.author.id)
    picks = nfl_picks if league.lower() == 'nfl' else cfb_picks
    if user_id in picks:
        picks[user_id] = new_pick
        save_picks()
        await ctx.send(f"{league.upper()} pick updated to: {new_pick}. {snarky_response} \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        await ctx.send(f"You don't have a {league.upper()} pick yet. Use `/addpick` to add one.\nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

@bot.command(name='deletepick')
async def delete_pick(ctx, league: str):
    user_id = str(ctx.author.id)
    picks = nfl_picks if league.lower() == 'nfl' else cfb_picks
    if user_id in picks:
        del picks[user_id]
        save_picks()
        await ctx.send(f"Your {league.upper()} pick has been deleted. {snarky_response} \nAvailable commands:\n'/addpick' <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        await ctx.send(f"You don't have a {league.upper()} pick to delete. \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

@bot.command(name='showpicks')
async def show_picks(ctx, league: str):
    picks = nfl_picks if league.lower() == 'nfl' else cfb_picks
    if not picks:
        await ctx.send(f"No {league.upper()} picks have been submitted yet. \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        response = "\n".join([f"<@{user}>: {pick}" for user, pick in picks.items()])
        await ctx.send(f"Current {league.upper()} picks:\n{response} \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

@bot.command(name='finalizeparlay')
@commands.has_permissions(administrator=True)
async def finalize_parlay(ctx):
    if not nfl_picks and not cfb_picks:
        await ctx.send("No picks to finalize. What a disappointing week! \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        response = ""
        if nfl_picks:
            response += "NFL Picks:\n" + "\n".join([f"<@{user}>: {pick}" for user, pick in nfl_picks.items()]) + "\n\n"
        if cfb_picks:
            response += "College Football Picks:\n" + "\n".join([f"<@{user}>: {pick}" for user, pick in cfb_picks.items()])
        await ctx.send(f"Parlay finalized with the following picks:\n{response}")

@bot.command(name='setadmin')
@commands.has_permissions(administrator=True)
async def set_admin(ctx, user: discord.Member):
    global admin_id
    admin_id = user.id
    await ctx.send(f"Admin privileges have been granted to <@{admin_id}> for managing weekly resets. \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

@bot.command(name='adminreset')
async def admin_reset(ctx):
    if ctx.author.id == admin_id:
        await trigger_weekly_reset(ctx)
    else:
        await ctx.send("You do not have permission to trigger the weekly reset. \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")

async def trigger_weekly_reset(ctx):
    global nfl_picks, cfb_picks
    if nfl_picks or cfb_picks:
        users_to_notify = list(nfl_picks.keys()) + list(cfb_picks.keys())
        mentions = " ".join([f"<@{user}>" for user in set(users_to_notify)])
        nfl_picks.clear()
        cfb_picks.clear()
        save_picks()
        await ctx.send(f"Weekly reset has been triggered. All previous picks have been cleared. {mentions}, the new week has started! \nAvailable commands:\n/addpick <league> <pick>, \n/editpick <league> <new_pick>, \n/deletepick <league>, \n/showpicks <league>")
    else:
        await ctx.send("No picks were found, but the weekly reset has been performed.")

@tasks.loop(hours=168)  # Weekly reset
async def weekly_reset():
    await trigger_weekly_reset(None)

bot.run(TOKEN)
