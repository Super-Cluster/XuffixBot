import dotenv
import os
import requests
import json
import random
import multibar
import time
import git
import threading

import disnake
from disnake.ext import commands

dotenv.load_dotenv()

token = os.getenv("token")

bot = commands.Bot(command_prefix=commands.when_mentioned_or("x."), intents=disnake.Intents().all(), help_command=None)
bot.remove_command("help")

if not os.path.exists("XuffixBot-repo"):
    git.Repo.clone_from("https://github.com/Super-Cluster/XuffixBot", "XuffixBot-repo")

REPO = git.Repo("XUffixBot-repo")

def get_data():
    return json.loads(open("data.json", "r").read())

def set_data(new:tuple):
    data = open("data.json", "w").write(json.dumps(new, indent=4))
    backup_data()
    return data

def get_data_key(key:str):
    return get_data()[key]

def set_data_key(key:str, value:object):
    data = get_data()
    data[key] = value
    return set_data(data)

def __backup_data():
    open("XuffixBot-repo/data.json", "w").write(json.dumps(get_data(), indent=4))
    open("XuffixBot-repo/__init__.py", "w").write(open("__init__.py", "r").read())
    REPO.index.add(["data.json", "__init__.py"])
    REPO.index.commit("Backup Data")
    origin = REPO.remote("origin")
    origin.push()

def backup_data():
    thread = threading.Thread(target=__backup_data)
    thread.start()

EMBED_COLOR = 0xFC61FF
OWNER_ID = 619464099775905795
GUILD_ID = 932050706712653902
MOD_CHANNEL = 932338678649487420
MEME_MODS = get_data_key("mods")
LOG_CHANNEL = 932355413595258961
OWNER_TAG = "Xuffix#3185"
RULES = f"- A meme must be funny\n- A meme must have a caption\n\nIf your meme got declined but you think it didn't break those rules, please contact ${OWNER_TAG}."

def get_rank(coins:int):
    if coins > 500:
        return "Meme God"
    elif coins > 100:
        return "Pro Memer"
    elif coins > 50:
        return "Memer"
    elif coins > 25:
        return "Intermediate"
    elif coins > 10:
        return "Beginner"
    else:
        return "Noob"

def get_next_rank(coins:int):
    if coins > 500:
        return "MAXED OUT"
    elif coins > 100:
        return "Meme God"
    elif coins > 50:
        return "Pro Memer"
    elif coins > 25:
        return "Memer"
    elif coins > 10:
        return "Intermediate"
    else:
        return "Beginner"

def get_next_rank_amount(coins:int):
    if coins > 500:
        return 0
    elif coins > 100:
        return 500
    elif coins > 50:
        return 100
    elif coins > 25:
        return 50
    elif coins > 10:
        return 25
    else:
        return 10

class AcceptMemeUI(disnake.ui.View):
    def __init__(self, user):
        super().__init__()
        self.value = None
        self.clicker = None

    @disnake.ui.button(label="Accept",emoji=disnake.PartialEmoji(id=932660388363911229,name="confirm"),style=disnake.ButtonStyle.grey)
    async def accept(self,button:disnake.ui.Button,inter:disnake.MessageInteraction):
        await inter.response.defer()

        for child in self.children:
            child.disabled = True

        await inter.edit_original_message(content="Accepted", view=self)

        self.value = True
        self.clicker = inter.author

        self.stop()

    @disnake.ui.button(label="Decline",emoji=disnake.PartialEmoji(id=932660388414255184,name="cancel"),style=disnake.ButtonStyle.grey)
    async def decline(self,button:disnake.ui.Button,inter:disnake.MessageInteraction):
        await inter.response.defer()

        for child in self.children:
            child.disabled = True

        await inter.edit_original_message(content="Declined", view=self)

        self.value = False
        self.clicker = inter.author

        self.stop()

async def modNextMeme(author):
    queue = get_data_key("queue")
    
    if len(queue) > 0:
        memes = get_data_key("memes")
        meme = queue[0]

        url = meme["url"]
        user = meme["user"]

        embed = disnake.Embed(title="Meme submited", color=EMBED_COLOR)
        embed.description = "Submitted by " + user
        embed.set_image(url)

        view = AcceptMemeUI(user)

        channel = bot.get_channel(MOD_CHANNEL)
        log_channel = bot.get_channel(LOG_CHANNEL)

        await channel.send(content="When the buttons stop working use `/pushqueue`", embed=embed, view=view)
        await view.wait()

        if view.value:
            memes.append({ "url": url, "user": user })
            set_data_key("memes", memes)

            coins = get_data_key("coins")
        
            found = False
            for user in coins:
                if user["id"] == author.id:
                    prevamount = user["amount"]
                    user["amount"] += 1
                    amount = user["amount"]
                    found = True

            if not found:
                prevamount = 0
                coins.append({ "id": author.id, "amount": 1 })
                amount = 1

            set_data_key("coins", coins)

            embed2 = disnake.Embed(title="Meme accepted", color=EMBED_COLOR)
            embed2.set_image(url)
            embed3 = embed2
            embed3.description = "Submitted by " + meme["user"] + "\nAccepted by " + view.clicker.mention
            await author.send(embed=embed2)
            await log_channel.send(embed=embed2)

            if get_rank(prevamount) != get_rank(amount):
                await author.send(f"You ranked up from {get_rank(prevamount)} to {get_rank(amount)}!")
        else:
            embed2 = disnake.Embed(title="Meme declined", color=EMBED_COLOR)
            embed2.set_image(url)
            embed3 = embed2
            embed3.description = "Submitted by " + meme["user"] + "\nDeclined by " + view.clicker.mention
            await author.send(embed=embed2)
            await log_channel.send(embed=embed3)

        queue = get_data_key("queue")
        queue.remove(meme)
        set_data_key("queue", queue)
        await modNextMeme(author)

@bot.message_command(name="Submit as meme", description="Submit meme")
async def app_submit(inter, message:disnake.Message):
    bans = get_data_key("bans")

    banned = False
    reason = ""
    for ban in bans:
        if ban["id"] == inter.author.id:
            banned = True
            reason = ban["reason"]

    print(requests.get(message.content).headers["content-type"] in ("image/png", "image/jpeg", "image/jpg"))
    print(requests.get(message.content).headers["content-type"])
    print(requests.get(message.content))
    print(message.content)
    
    try:
        if not banned:
            if len(message.attachments) > 0 or requests.get(message.content).headers["content-type"] in ("image/png", "image/jpeg", "image/jpg"):
                url = message.attachments[0].url if len(message.attachments) > 0 else message.content
                if requests.get(url).headers["content-type"] in ("image/png", "image/jpeg", "image/jpg"):
                    if get_data_key("open") == True:
                        memes = get_data_key("memes")
                        queue = get_data_key("queue")

                        found = False
                        for meme in memes:
                            if meme["url"] == url:
                                found = True

                        for meme in queue:
                            if meme["url"] == url:
                                found = True

                        if found:
                            await inter.response.send_message("This meme already exists, or is already in the queue.", ephemeral=True)
                        else:
                            await inter.response.send_message("Meme submitted.", ephemeral=True)

                            user = inter.author.name + "#" + inter.author.discriminator

                            queue.append({ "url": url, "user": user, "id": inter.author.id })
                            set_data_key("queue", queue)

                            if len(queue) == 1:
                                await modNextMeme(inter.author)
                    else:
                        await inter.response.send_message("Meme submitions have been closed. Please try again later.", ephemeral=True)
                else:
                    msg = "The URL you mentioned is not an image." if url else "The file you sent is not an image."
                    await inter.response.send_message(msg, ephemeral=True)
            else:
                await inter.response.send_message("This image does not have an attachment / valid image URL.", ephemeral=True)
        else:
            await inter.response.send_message(f"You have been banned from submitting memes.\nReason: {reason}", ephemeral=True)
    except Exception as e:
        await inter.response.send_message(f"```\n{e}\n```")

@bot.message_command(name="Submit as meme anonymously", description="Submit meme")
async def app_submit_anonymous(inter, message:disnake.Message):
    bans = get_data_key("bans")

    banned = False
    reason = ""
    for ban in bans:
        if ban["id"] == inter.author.id:
            banned = True
            reason = ban["reason"]

    if not banned:
        if len(message.attachments) > 0 and requests.get(message.content).headers["content-type"] not in ("image/png", "image/jpeg", "image/jpg"):
            url = message.attachments[0].url if len(message.attachments) > 0 else message.content
            if requests.get(url).headers["content-type"] in ("image/png", "image/jpeg", "image/jpg"):
                if get_data_key("open") == True:
                    memes = get_data_key("memes")
                    queue = get_data_key("queue")

                    found = False
                    for meme in memes:
                        if meme["url"] == url:
                            found = True

                    for meme in queue:
                        if meme["url"] == url:
                            found = True

                    if found:
                        await inter.response.send_message("This meme already exists, or is already in the queue.", ephemeral=True)
                    else:
                        await inter.response.send_message("Meme submitted.", ephemeral=True)

                        user = "an anonymous user"

                        queue.append({ "url": url, "user": user, "id": inter.author.id })
                        set_data_key("queue", queue)

                        if len(queue) == 1:
                            await modNextMeme(inter.author)
                else:
                    await inter.response.send_message("Meme submitions have been closed. Please try again later.", ephemeral=True)
            else:
                msg = "The URL you mentioned is not an image." if url else "The file you sent is not an image."
                await inter.response.send_message(msg, ephemeral=True)
        else:
            await inter.response.send_message("This image does not have an attachment.", ephemeral=True)
    else:
        await inter.response.send_message(f"You have been banned from submitting memes.\nReason: {reason}", ephemeral=True)

@bot.slash_command()
async def meme(inter):
    pass

@meme.sub_command(name="view", description="Get a meme")
async def memeview(inter, public:bool=False):
    meme = random.choice(get_data_key("memes"))

    embed = disnake.Embed(title="Meme", color=EMBED_COLOR)
    embed.description = f"Submitted by {meme['user']}"
    embed.set_image(meme["url"])

    await inter.response.send_message(embed=embed, ephemeral=not public)

@meme.sub_command(description="Submit meme")
async def submit(inter, url:str, anonymous:bool=False):
    bans = get_data_key("bans")

    banned = False
    reason = ""
    for ban in bans:
        if ban["id"] == inter.author.id:
            banned = True
            reason = ban["reason"]

    if not banned:
        if requests.get(url).headers["content-type"] in ("image/png", "image/jpeg", "image/jpg"):
            if get_data_key("open") == True:
                memes = get_data_key("memes")
                queue = get_data_key("queue")

                found = False
                for meme in memes:
                    if meme["url"] == url:
                        found = True

                for meme in queue:
                    if meme["url"] == url:
                        found = True

                if found:
                    await inter.response.send_message("This meme already exists, or is already in the queue.", ephemeral=True)
                else:
                    await inter.response.send_message("Meme submitted.", ephemeral=True)

                    user = "an anonymous user" if anonymous else inter.author.name + "#" + inter.author.discriminator

                    queue.append({ "url": url, "user": user, "id": inter.author.id })
                    set_data_key("queue", queue)

                    if len(queue) == 1:
                        await modNextMeme(inter.author)
            else:
                await inter.response.send_message("Meme submitions have been closed. Please try again later.", ephemeral=True)
        else:
            msg = "The URL you mentioned is not an image." if url else "The file you sent is not an image."
            await inter.response.send_message(msg, ephemeral=True)
    else:
        await inter.response.send_message(f"You have been banned from submitting memes.\nReason: {reason}", ephemeral=True)

@bot.slash_command(name="mod")
async def mod_(inter):
    await inter.response.defer()

@meme.sub_command(description="[MEME MOD ONLY] Adds a meme (this doesn't add coins)")
async def add(inter, url:str, user:disnake.User=None):
    if user == None:
        user = "an anonymous user"
    else:
        user = f"{user.name}#{user.discriminator}"

    if inter.author.id in MEME_MODS:
        memes = get_data_key("memes")

        found = False
        for meme in memes:
            if meme["url"] == url:
                found = True

        if not found:
            memes.append({ "url": url, "user": user })
            set_data_key("memes", memes)

            log_channel = bot.get_channel(LOG_CHANNEL)
            embed2 = disnake.Embed(title="Meme added", color=EMBED_COLOR)
            embed2.description = f"Meme by {user.name}#{user.discriminator}\nMeme added by {inter.author.mention}"
            embed2.set_image(url)
            await log_channel.send(embed=embed2)

            await inter.response.send_message("Meme added.", ephemeral=True)
        else:
            await inter.response.send_message("This meme already exists.", ephemeral=True)
    else:
        await inter.response.send_message("You are not a meme moderator.", ephemeral=True)

@meme.sub_command(description="[MEME MOD ONLY] Removes a meme (this doesn't remove coins)")
async def remove(inter, url:str):
    if inter.author.id in MEME_MODS:
        memes = get_data_key("memes")
        
        found = False
        for meme in memes:
            if meme["url"] == url:
                user = meme["user"]
                memes.remove(meme)
                found = True

        if found:
            set_data_key("memes", memes)

            log_channel = bot.get_channel(LOG_CHANNEL)
            embed2 = disnake.Embed(title="Meme removed", color=EMBED_COLOR)
            embed2.description = f"Meme by {user}\nMeme removed by {inter.author.mention}"
            embed2.set_image(url)
            await log_channel.send(embed=embed2)

            await inter.response.send_message("Meme removed.", ephemeral=True)
        else:
            await inter.response.send_message("This meme does not exist.", ephemeral=True)
    else:
        await inter.response.send_message("You are not a meme moderator.", ephemeral=True)

@bot.slash_command(description="[MEME MOD ONLY] Bans a person from submitting a meme")
async def ban(inter, user:disnake.User, reason:str="No reason provided"):
    bans = get_data_key("bans")

    found = False
    for ban in bans:
        if ban["id"] == user.id:
            found = True

    if inter.author.id in MEME_MODS:
        if not found:
            bans.append({ "id": user.id, "reason": reason })
            set_data_key("bans", bans)

            embed = disnake.Embed(title="You have been banned", color=EMBED_COLOR)
            embed.description = f"You cannot submit any memes anymore.\nReason: {reason}"
            await user.send(embed=embed)

            log_channel = bot.get_channel(LOG_CHANNEL)
            embed2 = disnake.Embed(title="User banned", color=EMBED_COLOR)
            embed2.description = f"{user.mention} has been banned by {inter.author.mention}\nReason: {reason}"
            await log_channel.send(embed=embed2)

            await inter.response.send_message(f"{user.mention} has been banned.", ephemeral=True)
        else:
            await inter.response.send_message("This user has already been banned.", ephemeral=True)
    else:
        await inter.response.send_message("You are not a meme moderator.", ephemeral=True)

@bot.slash_command(description="[MEME MOD ONLY] Unbans a person from submitting a meme")
async def unban(inter, user:disnake.User, reason:str="No reason provided."):
    bans = get_data_key("bans")

    found = False
    for ban in bans:
        if ban["id"] == user.id:
            found = True

    if inter.author.id in MEME_MODS:
        if found:
            for ban in bans:
                if ban["id"] == user.id:
                    bans.remove(ban)

            set_data_key("bans", bans)

            embed = disnake.Embed(title="You have been unbanned", color=EMBED_COLOR)
            embed.description = f"You can submit memes again.\nReason: {reason}"
            await user.send(embed=embed)
            
            log_channel = bot.get_channel(LOG_CHANNEL)
            embed2 = disnake.Embed(title="User unbanned", color=EMBED_COLOR)
            embed2.description = f"{user.mention} has been unbanned by {inter.author.mention}\nReason: {reason}"
            await log_channel.send(embed=embed2)

            await inter.response.send_message(f"{user.mention} has been unbanned.", ephemeral=True)

        else:
            await inter.response.send_message("This user isn't banned.", ephemeral=True)
    else:
        await inter.response.send_message("You are not a meme moderator.", ephemeral=True)

@bot.slash_command(description="Get the stats of a user")
async def stats(inter, user:disnake.User=None, public:bool=False):
    if user == None:
        user = inter.author

    coins = get_data_key("coins")
    amount = 0
        
    for u in coins:
        if u["id"] == user.id:
            amount = u["amount"]

    next_amount = get_next_rank_amount(amount)

    if next_amount == 0:
        progress = get_rank(amount)
    else:
        bar = multibar.ProgressBar(amount / get_next_rank_amount(amount) * 100, 100)
        progress = f"{get_rank(amount)} {bar.write_progress(**multibar.ProgressTemplates.DEFAULT)} {get_next_rank(amount)}"

    embed = disnake.Embed(title=f"Stats", color=EMBED_COLOR)
    embed.description = progress
    embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url)
    embed.add_field(name="Coins", value=str(amount))

    await inter.response.send_message(embed=embed, ephemeral=not public)

@bot.slash_command(description="Shows all the ranks you can get")
async def ranks(inter):
    await inter.response.send_message("Meme God: 500 coins\nPro Memer: 100 coins\nMemer: 50 coins\nIntermediate: 25 coins\nBeginner: 10 coins\nNoob: 0 coins", ephemeral=True)

@bot.slash_command(description="Shows how many coins a user has")
async def coins(inter):
    pass

@coins.sub_command(name="set", description="[BOT OWNER ONLY] Sets coin amount of user")
async def setcoins(inter, amount:int, user:disnake.User=None):
    if user != None:
        user = user.id
    else:
        user = inter.author.id

    if inter.author.id == OWNER_ID:
        coins = get_data_key("coins")

        for u in coins:
            if u["id"] == user:
                coins.remove(u)

        coins.append({ "id": user, "amount": amount })
        set_data_key("coins", coins)

        await inter.response.send_message("Done.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@mod_.sub_command(description="[MEME MOD ONLY] Pushes from queue.")
async def pushqueue(inter):
    if inter.author.id in MEME_MODS:
        queue = get_data_key("queue")
        if len(queue) > 0:
            await inter.response.send_message("Done.", ephemeral=True)
            user = await bot.get_or_fetch_user(queue[0]["id"])
            await modNextMeme(user)
        else:
            await inter.response.send_message("The queue is empty.", ephemeral=True)
    else:
        await inter.response.send_message("You are not a meme moderator.", ephemeral=True)

@bot.slash_command(name="open" ,description="[BOT OWNER ONLY] Open meme submitions")
async def command_open(inter):
    if inter.author.id == OWNER_ID:
        set_data_key("open", True)
        await inter.response.send_message("Meme submitions have been opened.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@bot.slash_command(description="[BOT OWNER ONLY] Close meme submitions")
async def close(inter):
    if inter.author.id == OWNER_ID:
        set_data_key("open", False)
        await inter.response.send_message("Meme submitions have been closed.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@bot.slash_command(description="[BOT OWNER ONLY] Stops the bot")
async def stop(inter):
    if inter.author.id == OWNER_ID:
        await inter.response.send_message("Bot has stopped.", ephemeral=True)
        exit()
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@bot.slash_command(description="View the rules of memes")
async def rules(inter):
    await inter.response.send_message(RULES, ephemeral=True)

@mod_.sub_command(name="add", description="[BOT OWNER ONLY] Adds a meme moderator")
async def addmod(inter, user:disnake.User):
    global MEME_MODS
    if inter.author.id == OWNER_ID:
        member = await bot.get_guild(GUILD_ID).get_or_fetch_member(user.id)

        if member != None:
            await member.add_roles(disnake.Object(932338504602644572))

            mods = get_data_key("mods")

            found = False
            for mod in mods:
                if mod == user.id:
                    found = True

            if not found:
                mods.append(user.id)
                set_data_key("mods", mods)
                MEME_MODS = mods

                await user.send(f"You are now a meme moderator! You can now accept/decline memes!\n\nDon't forgot the rules though:\n{RULES}")

                await inter.response.send_message(f"Added {user.mention} as a meme moderator.", ephemeral=True)
            else:
                await inter.response.send_message(f"{user.mention} is already a meme moderator.", ephemeral=True)
        else:
            await inter.response.send_message(f"{user.mention} is not in the main guild.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@mod_.sub_command(name="remove", description="[BOT OWNER ONLY] Removes a meme moderator")
async def removemod(inter, user:disnake.User, reason:str="No reason provided"):
    global MEME_MODS
    if inter.author.id == OWNER_ID:
        member = await bot.get_guild(GUILD_ID).get_or_fetch_member(user.id)

        if member != None:
            await member.remove_roles(disnake.Object(932338504602644572))

            mods = get_data_key("mods")

            for mod in mods:
                if mod == user.id:
                    mods.remove(mod)

            set_data_key("mods", mods)

            MEME_MODS = mod

            await user.send(f"You are not a meme moderator anymore. Reason: {reason}")

            await inter.response.send_message(f"Removed {user.mention} from the meme moderator list.", ephemeral=True)
        else:
            await inter.response.send_message(f"{user.mention} is not in the main guild.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@bot.slash_command(description="[BOT OWNER ONLY] Backup bot data")
async def backup(inter):
    if inter.author.id == OWNER_ID:
        backup_data()
        await inter.response.send_message("Done.", ephemeral=True)
    else:
        await inter.response.send_message("You are not the bot owner.", ephemeral=True)

@bot.event
async def on_slash_command_error(inter, error):
    if isinstance(error, (commands.MissingAnyRole, commands.BadArgument, commands.CommandNotFound)):
        await inter.response.send_message(f"{error}", ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
        await inter.response.send_message(f"PermissionError: Bot missing Permissions", ephemeral=True)
    elif isinstance(error, commands.BotMissingAnyRole):
        await inter.response.send_message(f"PermissionError: Bot missing any role", ephemeral=True)
    elif isinstance(error, commands.BotMissingRole):
        await inter.response.send_message(f"PermissionError: Bot missing role", ephemeral=True)
    elif isinstance(error, commands.CommandInvokeError):
        if "MissingSchema" in str(error):
            await inter.response.send_message(f"Invalid URL", ephemeral=True)
        else:
            user = await bot.get_or_fetch_user(OWNER_ID)
            await user.send(content=f"An error has occured.\n```\n{error}\n```")
            await inter.response.send_message(f"Something went wrong when running this command. The error has been sent to the developer.\n```\n{error}\n```", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Started {bot.user}")
    await bot.change_presence(activity=disnake.Activity(name="with your dick", type=disnake.ActivityType.playing, timestamps={ "start": time.time() }))

bot.run(token)