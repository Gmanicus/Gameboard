# -*- coding: utf-8 -*-

# Gameboard Discord Bot
# - Grant "Gmanicus" Scrits at Geek Overdrive Studios

# Thanks for checking out my code.

# Pinterest library
from py3pin.Pinterest import Pinterest

# Libraries for parsing
import json
from parse import *
import play_scraper
import requests
from requests_html import AsyncHTMLSession

# Scheduling and memory cleanup libraries
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import gc

# Bot
import discord
from discord.ext import commands
from discord.ext.commands import Bot

# General libraries
import asyncio
import random
import time
import datetime
import math
import os
import re
import string

# Server ID : Entry Channel ID, Promo Channel ID, Last Poke Msg, Admin User IDs, Do Not Disturb Users
server_data = {}

# User queue for saving what stage of the entry process that users are on and what answers they've given. Used to allow multiple users to make entries at one time
user_queue = {}

# A queue of jobs, as Pinterest rate limits board, pin, section creations and successful logins after about 10 times
# This allows us to keep a list of all the things that failed to go through and put them through when the rate limit is lifted.
# On the other hand, this also gives us a fail-safe method of recovering all the entries if, say, the API changes and our system fails every time
job_queue = []

class server_info:
    entry = 0
    promo = 1
    last_poke = 2
    admins = 3
    DNDs = 4

    # Entry channel ID
    # Promo channel ID
    # ID of the last poke message sent. Used for cleanup.
    # Admin user IDs
    # IDs of Users who requested "Do Not Disturb"


# Class for storing message info 
# -- Is this a direct message? 
# -- Server this msg came from 
# -- Channel this msg came from
# -- Msg this msg came from... wait wut? 
# -- ID of the author of this msg Actual text of the msg
class message_info:
    direct = False
    server_id = ""
    channel_id = ""
    message_obj = None
    author_id = ""
    value = ""

# Class for storing user queue data
# -- Stage the user is on in entry process
# -- Table of the answers user has given
# -- String with a list of sections given at the end of the stage questions
class user_in_queue:
    def __init__(self):
        self.stage = 0
        self.answers = []
        self.sections_given = None

# Class for storing server data
class server_cache:
    def __init__(self):
        self.setup = False
        self.board = None
        self.sections = {}
        self.entry = None
        self.promo = None
        self.admin_role = None
        # Add ourselves so that we don't have a recursion issue
        self.dnd_users = ["658509820957032458"]

# A list of currency symbols for string checks
currency_symbols = ["$", "€", "¥", "₤", "£", "¢", "¤", "฿", "৳", "₠", "Free"]


# The command prefix of the bot. This is what you preface with to make commands go through to the bot. E.g: "!help", "!entry"
callsign = "gb>"

# A list of commands for help messages
command_list = (
    "`{0}what`: Information about Gameboard.\n"
    "`{0}help`: This message.\n"
    "`{0}entry`: Add a game to the Gameboard\n"
    "`{0}dnd`: (Do Not Disturb) Opt-out of reminders when posting in the promotion channel.\n"
    "`{0}board`: Get the link to this community's board.\n"
).format(callsign)

what_am_i = (
    "Hi, I'm Gameboard. I was created by Gmanicus#5137 (@GeekOverdriveUS).\n\n"
    "I was created to compile a list of games and their details in hopes of keeping a history of the communities' games, and also help promote them more. "
    "It was actually a bit successful when initially made in Oct. 2018, displaying info via a Google Docs page. I do not know how successful it was at promotion, but it was utilized quite a bit. "
    "\n\nThis overhaul hopes to improve on promotion even more. The code is much nicer now, available on Github under 'Gmanicus', and, most importantly, I now use a Pinterest board instead of Google Docs. "
    "This greatly improves the visability of games posted to Gameboard and gives them a pretty outlet to be shown from.\n\n"
    "If you would like to support the developer behind this, feel free to stop by on his Patreon. <https://www.patreon.com/user?u=11363490>"
)

# A list of questions to ask in order to make a Gameboard entry
stage_questions = [

    ":mag: <@{0}> Please input the **Link** to the project.",
    ":id: <@{0}> {1}Please input the **Project Title**.",
    ":speech_balloon: <@{0}> {1}Please input the **Description** of the project.",
    ":bow: <@{0}> {1}Please input the **Studio Name**.",
    ":dollar: <@{0}> {1}Please input the **Price** of the project.",
    ":moneybag: <@{0}> {1}Please input the **Currency Symbol** for the price.",
    ":bookmark: <@{0}> {1}Please input the link to the **Store Image** of the project.",
    ":bookmark_tabs: <@{0}> Lastly, where do you want this put? Please select a section to place this in via the corresponding number.\n\n{1}",
    ":heart: <@{0}> Thank you for submitting your project!" # ":pencil: Use `{callsign}editentry <entrynum>` to update information on your entry."

]

# Found and Not Found formats to say when going through the stage questions
found_format = "I found `{0}`. If this is correct, say `yes`. Otherwise, "
special_found_format = "I found {0} . If this is correct, say `yes`. Otherwise, "
not_found_format = "I couldn't find this. "


step1_setup_msg = (":100: Your server's gameboard has been created and named **{0}**.\n\n"
                "Please add what channels I'm allowed to operate in. You can set these via `{1}setentry <channel_id>` and `{1}setpromo <channel_id>`.\n\n"
                "`setentry` sets the channel that Gameboard looks to for board entries. That way, entries are only made in one place and it doesn't look as messy.\n\n"
                "`setpromo` sets the channel that Gameboard looks to for potential board entries. "
                "If Gameboard recognizes that there was a game post made there, it will let the user know that they can add it to the community gameboard. "
                "The user can use the `{1}dnd` command to keep the bot from pinging them for this if they like.")

step2_setup_msg = "\n:white_square_button: Now please set the {0} channel via `{1}set{0} <channel_id>`"

step3_setup_msg = ("\n:white_square_button: Lastly, please create a section or two via `{0}addsection <section name>` for your community to post entries to.\n\n"
                "Users will only be able to add entries to these sections, so create them wisely and as needed.\n"
                "Get creative. Sections can be used to group things as you like.\n"
                "They can be used to group games to events, like **New Year Jam 2020** or **LD Jam 69**, or you can simply create a single section, like **Our Community's Games**.")

end_setup_msg = ("\n:white_check_mark: Great! The **{0}** gameboard can now be used, although please feel free to continue adding sections and or change the `entry` and `promo` channel IDs. "
                "Please enjoy using Gameboard. Contact Gmanicus#5137 or @GeekOverdriveUS if you have any issues or suggestions.")

board_base_desc = "This board was created for the {0} game development community. Check out their games here!"

py3pin_link = "https://www.pinterest.com/pin/{0}/"
py3board_link = "https://www.pinterest.com/gameboardbot/{0}/"

# This is checked periodically. If there is over an hour since the time in this var,
# the hour start time is reset to the current time. This is used to calculate avg stuff over the last hour
hour_start_time = 0

new_entries = 0
new_boards = 0
new_sections = 0
command_calls = 0


servers = []

bot = commands.Bot(command_prefix=callsign)

bot.remove_command("help")


""" |/ TO DO \|

/// POLISH:

Allow admins to add a role to give control over the gameboard

Allow users to search for random pin, or random pins from specific genres

Allow users to edit their own pins

Allow users to submit with no link


"""





def main():
    gc.disable()
    gc.set_debug(gc.DEBUG_STATS)

    global hour_start_time
    hour_start_time = time.time()

    email = ""
    password = ""
    username = ""

    with open("credentials.txt", "r") as creds_file:
        creds = eval(creds_file.read())

        global BOT_TOKEN
        BOT_TOKEN = creds["token"]
        email = creds["email"]
        password = creds["password"]
        username = creds["username"]

    # Load stored data backups
    load_backup()

    # Begin Pinterest authentication
    global pinterest
    pinterest = Pinterest(email=email,
                        password=password,
                        username=username)

    print("\nIf you're seeing this, we logged in SUCCESSFULLY\n")

    # Login to Pinterest. Allows us to make changes
    #pinterest.login()

@bot.event
async def on_ready():
    global servers
    servers = bot.servers

    await bot.change_presence(game=discord.Game(name="{0}help".format(callsign)))


@bot.event
async def on_server_join(server):
    # Get the admin member so we can send him a message
    admin = get_owner(server)

    print("I was invited to the {0} server.".format(server.name))

    if not server.id in server_data:
        # Create a new server_cache object in the server data variable under this server's ID
        server_data[server.id] = server_cache()

        create_board(
            server_id=server.id,
            name=server.name,
            description=board_base_desc.format(server.name)
        )

        # Backup the server data now that we've made changes
        backup()

        await bot.send_message(admin, step1_setup_msg.format(server.name, callsign))
    else:
        await bot.send_message(admin, ":100: Welcome back! Your community's board has been recovered!")


@bot.event
async def on_message(chat):
    # If it has been more than an hour since our last hour_start_time
    global hour_start_time
    global new_entries
    global new_boards
    global new_sections
    global command_calls
    if time.time() - hour_start_time > 3600:
        hour_start_time = time.time()
        print("\n\n**There have been {0} entries, {1} boards, {2} sections created, and {3} command calls over the past hour**\n\n".format(new_entries, new_boards, new_sections, command_calls))
        command_calls = 0
        new_entries = 0
        new_boards = 0
        new_sections = 0

    # First wait and allow Discord to check whether a command needs to be run
    await bot.process_commands(chat)

    # If this message is a command, we don't want to run anything in on_message.
    # This should already have a dedicated function to deal with it, so we don't want to process it a second time
    if is_command(chat):
        return

    # Get msg data and put it in our custom class
    msg = get_msg_data(chat)

    # Just verify that this was posted within a channel we are permitted to work in
    foo, channel = is_msg_for_me(msg)

    if foo and channel == server_info.entry:
        if is_user_in_queue(msg.author_id):
            await update_entry(msg)

    # If we are in promo, user is not in Do not Disturb, and we use some keywords while not others, ping them and let them know they can use the board.
    if foo and channel == server_info.promo:
        if msg.author_id not in server_data[msg.server_id].dnd_users:
            if "game " in msg.value.lower() or "project " in msg.value.lower() or "release " in msg.value.lower() or "steampowered" in msg.value.lower() or "itch.io" in msg.value.lower():
                if "twitch" not in msg.value.lower() and "video" not in msg.value.lower():
                    await bot.send_message(bot.get_channel(server_data[msg.server_id].entry), (
                        "<@{0}> Gameboard lists games on Pinterest. Would you like to add your project to this community's Gameboard? "
                        "Use `{1}entry`.\nUse `{1}dnd` if you would prefer not to see this message."
                        ).format(msg.author_id, callsign))


# Set the community's entry channel
@bot.command(pass_context=True)
async def setentry(ctx, *channel_id):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    # Get the server(s) this user owns, if any
    owned, num_owned, input = get_user_owned_servers(msg, channel_id)

    input = input[0]

    # Check to see if we can access the given channel. Discord API will return none when trying to get a channel we can't access
    if not bot.get_channel(input):
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: I couldn't find that channel. Please try again.")
        return

    # If we found a mutual server where the user is an admin, continue. Otherwise, let them know they can't do this.
    if owned and num_owned == 1:
        await bot.send_message(bot.get_channel(msg.channel_id), ":white_check_mark: Set entry channel as: **{0}**".format(bot.get_channel(input).name))
        # Set this server's entry channel ID as the given ID
        server_data[owned[0].id].entry = input

        # Backup the server data now that we've made changes
        backup()

        # If we haven't set the promo channel yet, proceed with setup step 2, otherwise, move to step 3
        if not server_data[owned[0].id].promo:
            await bot.send_message(bot.get_channel(msg.channel_id), step2_setup_msg.format("promo", callsign))
        else:
            await bot.send_message(bot.get_channel(msg.channel_id), step3_setup_msg.format(callsign))
    elif num_owned > 1:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: It appears you administrate multiple servers that I am a member of.\nSince this is a private channel and I don't know what server this is for, please try again in the format: `{0}setentry <server_id> <channel_id>`".format(callsign))
    elif not owned:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: Only admins are permitted to set proporties for the Gameboard.")


# Set the community's promo channel
@bot.command(pass_context=True)
async def setpromo(ctx, *channel_id):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    # Get the server(s) this user owns, if any
    owned, num_owned, input = get_user_owned_servers(msg, channel_id)

    input = input[0]


    # Check to see if we can access the given channel. Discord API will return none when trying to get a channel we can't access
    if not bot.get_channel(input):
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: I couldn't find that channel. Please try again.")
        return

    # If we found a mutual server where the user is an admin, continue. Otherwise, let them know they can't do this.
    if owned and num_owned == 1:
        await bot.send_message(bot.get_channel(msg.channel_id), ":white_check_mark: Set promo channel as: **{0}**".format(bot.get_channel(input).name))
        # Set this server's promo channel ID as the given ID
        server_data[owned[0].id].promo = input

        # Backup the server data now that we've made changes
        backup()

        # If we haven't set the entry channel yet, proceed with setup step 2, otherwise, move to step 3
        if not server_data[owned[0].id].entry:
            await bot.send_message(bot.get_channel(msg.channel_id), step2_setup_msg.format("entry", callsign))
        else:
            await bot.send_message(bot.get_channel(msg.channel_id), step3_setup_msg.format(callsign))
    elif num_owned > 1:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: It appears you administrate multiple servers that I am a member of.\nSince this is a private channel and I don't know what server this is for, please try again in the format: `{0}setpromo <server_id> <channel_id>`".format(callsign))
    elif not owned:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: Only admins are permitted to set proporties for the Gameboard.")


# Add a section to a community's gameboard
@bot.command(pass_context=True)
async def addsection(ctx, *name):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    # Get the server(s) this user owns, if any
    owned, num_owned, input = get_user_owned_servers(msg, name)

    # If we found a mutual server where the user is an admin, continue. Otherwise, let them know they can't do this.
    if owned and num_owned == 1:
        title = " ".join(input)
        title = title.title()

        status = create_board_section(
            server_id=owned[0].id,
            board_id=server_data[owned[0].id].board,
            section_name=title
        )

        if status:
            await bot.send_message(bot.get_channel(msg.channel_id), ":white_check_mark: Added Gameboard section named: **{0}**".format(title))
        else:
            await bot.send_message(bot.get_channel(msg.channel_id), ":yellow_square: Accepted Gameboard section named: **{0}**.\nHowever, it may take some time before it appears on Pinterest and board entries.".format(title))

        # Backup the server data now that we've made changes
        backup()

        # If we've set the channel IDs, send the server setup completion message
        if server_data[owned[0].id].entry and not server_data[owned[0].id].setup:
            await bot.send_message(bot.get_channel(msg.channel_id), end_setup_msg.format(owned[0].name))
            server_data[owned[0].id].setup = True

    elif num_owned > 1:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: It appears you administrate multiple servers that I am a member of.\nSince this is a private channel and I don't know what server this is for, please try again in the format: `{0}addsection <server_id> <section name>`".format(callsign))
    elif not owned:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: Only admins are permitted to add sections to the Gameboard.")



# Set the community's entry channel
@bot.command(pass_context=True)
async def data(ctx):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    # Get the server(s) this user owns, if any
    owned, num_owned, foo = get_user_owned_servers(msg)

    entry = None
    promo = None

    if bot.get_channel(server_data[owned[0].id].entry):
        entry = bot.get_channel(server_data[owned[0].id].entry).name

    if bot.get_channel(server_data[owned[0].id].promo):
        promo = bot.get_channel(server_data[owned[0].id].promo).name

    if owned:
        await bot.send_message(bot.get_channel(msg.channel_id), (":bookmark_tabs: **{0}** server has this data stored:\n\n"
                                                            "**Entry Channel Name**: {1}\n"
                                                            "**Promo Channel Name**: {2}\n"
                                                            "**Section Names**: {3}\n").format(owned[0].name, entry, promo, get_section_list_string(owned[0].id)))
    else:
        await bot.send_message(bot.get_channel(msg.channel_id), ":x: I could not find that server")




@bot.command(pass_context=True)
async def entry(ctx):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    global new_entries
    new_entries+=1

    # Just verify that this was posted within a channel we are permitted to work in
    foo, channel = is_msg_for_me(msg)

    send = None

    # If we are permitted in this channel and the channel is the entry channel
    if foo and channel == server_info.entry:
        # If the user isn't already making an entry
        if not is_user_in_queue(msg.author_id):
            # If there are sections available
            if get_section_list_string(msg.server_id):
                # Add them to the queue
                user_queue[msg.author_id] = user_in_queue()
                # And start making an entry for them
                await update_entry(msg)
            else:
                send = ":x: I'm sorry, there are no sections available to add entries to. Please contact server administrators and have them make some."
        # If the user IS already making an entry
        else:
            # Let the user know that they've already started making an entry
            send = ":x: You're already making an entry <@{0}>!\nType `exit` if you would like to cancel this entry.".format(msg.author_id)
    else:
        name = bot.get_channel(server_data[msg.server_id].entry)
        if name:
            name = name.name
        send = ":x: You can't make entries in this channel <@{0}>.\nPlease use this command in a direct message or in **{1}**".format(msg.author_id, name)

    if send:
        # Get the channel object that the user sent the message from
        channel = bot.get_channel(msg.channel_id)

        response = await bot.send_message(channel, send)
        await asyncio.sleep(5)
        await bot.delete_message(ctx.message)
        await bot.delete_message(response)


@bot.command(pass_context=True)
async def dnd(ctx):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    server_data[msg.server_id].dnd_users.append(msg.author_id)

    await bot.send_message(ctx.message.channel, ":zzz: I will no longer disturb you, {0}".format(ctx.message.author.name))

@bot.command(pass_context=True)
async def board(ctx):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    if bot.get_server(msg.server_id):
        boardname = bot.get_server(msg.server_id).name
        boardname = boardname.replace("\\", "")
        boardname = boardname.replace("/", "")
        boardname = boardname.replace(" ", "-")
        boardname = boardname.replace("--", "-")
        boardname = boardname.replace("--", "-")
        boardname = boardname.lower()

        await bot.send_message(ctx.message.channel, ":white_check_mark: Here ya go! " + py3board_link.format(boardname))
    else:
        await bot.send_message(ctx.message.channel, ":x: I don't know what server you're trying to get the board for. Please use this in the server you want to get the board for.")

@bot.command(pass_context=True)
async def help(ctx):
    global command_calls
    command_calls+=1
    msg = get_msg_data(ctx.message)

    await bot.send_message(ctx.message.channel, command_list)

@bot.command(pass_context=True)
async def what(ctx):
    global command_calls
    command_calls+=1

    msg = get_msg_data(ctx.message)

    await bot.send_message(ctx.message.channel, what_am_i)

# Get data from message context and put it in our custom class
def get_msg_data(message):
    msg = message_info()

    # If this message does not come from a server, recognize that it is a direct message
    try:
        if message.channel.server is not None:
            msg.server_id = message.channel.server.id
    except:
        msg.direct = True
    msg.channel_id = message.channel.id
    msg.message_obj = message
    msg.author_id = message.author.id
    msg.value = message.content

    return msg




# Add and update entries for the Gameboard
async def update_entry(msg):
    # If we are on stage one and haven't link scraped yet
    if user_queue[msg.author_id].stage == 1:
        user_queue[msg.author_id].answers.append(msg.value)

    # If this is the second stage, where the response should've been the project link...
    if user_queue[msg.author_id].stage == 1:
        # Scrape data on that url
        data, foo, reason = scrape_data(user_queue[msg.author_id].answers[0])

        # If the scrape returns with a bad foo, remove user's answer and allow them to answer again
        # The foo value basically tells us whether the link they provided was good or not
        if not foo and reason:
            send = ":x: " + reason + ". Please try with a different link, or try again."
            channel = bot.get_channel(msg.channel_id)
            await bot.send_message(channel, send)
            user_queue[msg.author_id].answers.pop(0)
            return
        # If the scrape returns with a bad foo, but there is no reason (which signifies that the URL is ok and the scrape just didn't get everything)
        # Fill out the answers and prompt the user to add missing info
        elif not foo and not reason or foo:
            user_queue[msg.author_id].answers.append(data["title"])
            user_queue[msg.author_id].answers.append(data["desc"])
            user_queue[msg.author_id].answers.append(data["studio"])
            user_queue[msg.author_id].answers.append(data["price"])
            user_queue[msg.author_id].answers.append(data["currency"])
            user_queue[msg.author_id].answers.append(data["img_link"])
            user_queue[msg.author_id].answers.append(None)

        # If the scrape was perfect and answered all of the questions
        if foo:
            user_queue[msg.author_id].stage = len(stage_questions)-2

    answer = None

    # If this is not the first or last stage question
    if user_queue[msg.author_id].stage != 0 and user_queue[msg.author_id].stage != len(stage_questions)-1:
        # Get the answer to this question
        last_answer = user_queue[msg.author_id].answers[user_queue[msg.author_id].stage-1]

        # If the answer to this stage's question has not been filled out
        if not last_answer:
            user_queue[msg.author_id].answers[user_queue[msg.author_id].stage-1] = msg.value
        
        # Adjust the stage to the next value we couldn't find while scraping
        user_queue[msg.author_id].stage = get_first_null_value(user_queue[msg.author_id].answers)

        # If we are not skipping to the last question, update the answer to the correct one
        if user_queue[msg.author_id].stage != len(stage_questions)-1:
            answer = user_queue[msg.author_id].answers[user_queue[msg.author_id].stage]

        """ 
        else
            # If the user did not accept the answer we procured via scraping...
            if "yes" not in msg.value.lower() and "y" not in msg.value.lower():

                # If the last stage was the stage where we asked for the price of the project
                if user_queue[msg.author_id].stage-1 == 4:
                    msg.value = costify(msg.value)
                # Set last stage's answer to what the user responded with
                user_queue[msg.author_id].answers[user_queue[msg.author_id].stage-1] = msg.value
        """

        print(user_queue[msg.author_id].answers)

    # Send this stage's message and format in the user's ID to mention them.
    send = stage_questions[user_queue[msg.author_id].stage]

    # If this is not the first, second to last, or last stage question
    if user_queue[msg.author_id].stage != 0 and user_queue[msg.author_id].stage < len(stage_questions)-2:
        # If we were able to answer this question via our scraping methods
        if answer:
            # If this is the img_link stage, use found format without `` around answer
            if user_queue[msg.author_id].stage == 6:
                send = send.format(msg.author_id, special_found_format.format(answer))
            else:
                send = send.format(msg.author_id, found_format.format(answer))
        # If we were NOT able to answer this question via our scraping methods
        else:
            send = send.format(msg.author_id, not_found_format.format(answer))
    # If this is the stage question where we ask for the section
    elif user_queue[msg.author_id].stage == len(stage_questions)-2:
        section_list = get_section_list_string(msg.server_id)

        user_queue[msg.author_id].sections_given = section_list

        send = send.format(msg.author_id, section_list)
    # If this is the submit stage
    elif user_queue[msg.author_id].stage == len(stage_questions)-1:
        send = send.format(msg.author_id)

        section_id = get_section_id(msg.server_id, user_queue[msg.author_id].sections_given, msg.value)
        if not section_id:
            channel = bot.get_channel(msg.channel_id)
            await bot.send_message(channel, ":x: That section wasn't found. Please try again.")
            return

        description = "{0} - ({1}) is a game made by {2}: {3}".format(user_queue[msg.author_id].answers[1],
                                                                    user_queue[msg.author_id].answers[4],
                                                                    user_queue[msg.author_id].answers[3],
                                                                    user_queue[msg.author_id].answers[2])

        status, id = upload_pin(discord_user=bot.get_user_info(msg.author_id),
                board_id=server_data[msg.server_id].board,
                section_id=section_id,
                image_url=user_queue[msg.author_id].answers[6],
                description=description,
                title=user_queue[msg.author_id].answers[1],
                link=user_queue[msg.author_id].answers[0])

        if not status:
            appendage = "\n\n:yellow_square: I've accepted your entry. However, it may take a little while to appear on Pinterest right now. I will PM you with a link when it has been uploaded."
        else:
            appendage = "\n\n:white_check_mark: I've uploaded your Gameboard entry. You can see it here: {0}".format(py3pin_link.format(id))

        send += appendage
    else:
        send = send.format(msg.author_id)

    await bot.delete_message(msg.message_obj)

    # Get the channel object that the user sent the message from
    channel = bot.get_channel(msg.channel_id)

    await bot.send_message(channel, send)

    # If we are on the last stage ("Thanks for submitting"), remove this user from the user_queue, as they have finished their entry
    if user_queue[msg.author_id].stage == len(stage_questions)-1:
        del user_queue[msg.author_id]
    # Otherwise, increment the stage.
    else:
        user_queue[msg.author_id].stage += 1
    

# Send message to specified channel within a specified server
async def send_channel_message(server_id, msg, msg_type):
    if server_id in server_data:
        if msg_type == server_info.entry:
            # Get channel object for requested server and channel destination
            channel = bot.get_channel(server_data[server_id].entry)
        if msg_type == server_info.promo:
            # Get channel object for requested server and channel destination
            channel = bot.get_channel(server_data[server_id].promo)
        await bot.send_message(channel, msg)


# Backup all of the data
def backup():
    serializable_data = {}

    with open("server_data.json", "w") as server_data_file:
        for id in server_data:
            serializable_data[id] = {}

            serializable_data[id]["setup"] = server_data[id].setup
            serializable_data[id]["board"] = server_data[id].board
            serializable_data[id]["sections"] = server_data[id].sections
            serializable_data[id]["entry"] = server_data[id].entry
            serializable_data[id]["promo"] = server_data[id].promo
            serializable_data[id]["admin_role"] = server_data[id].admin_role
            serializable_data[id]["dnd_users"] = server_data[id].dnd_users

        json.dump(serializable_data, server_data_file)

# Load all of the backup data
def load_backup():
    json_data = {}

    with open("server_data.json", "r") as server_data_file:
        try:
            json_data = json.load(server_data_file)

            for id in json_data:
                server_data[id] = server_cache()

                server_data[id].setup = json_data[id]["setup"]
                server_data[id].board = json_data[id]["board"]
                server_data[id].sections = json_data[id]["sections"]
                server_data[id].entry = json_data[id]["entry"]
                server_data[id].promo = json_data[id]["promo"]
                server_data[id].admin_role = json_data[id]["admin_role"]
                server_data[id].dnd_users = json_data[id]["dnd_users"]
        except:
            print("\n**I couldn't access the backup.**\n")

# Do the jobs in the job queue. This runs every 30mins
async def do_jobs():
    x = 0
    org_max = len(job_queue)
    if org_max > 0:
        print("\nDoing Jobs: {0} total.".format(org_max))
    job_max=len(job_queue)-1
    for job in job_queue:
        if "pin" in job:
            status, id = upload_pin(discord_user=job["pin"]["discord_user"],
                        board_id=job["pin"]["board_id"],
                        section_id=job["pin"]["section_id"],
                        image_url=job["pin"]["image_url"],
                        description=job["pin"]["description"],
                        title=job["pin"]["title"],
                        link=job["pin"]["link"])

            if status:
                await bot.send_message(job["pin"]["discord_user"], ":white_check_mark: Thanks for your entry to the Gameboard! I've uploaded your Gameboard entry. You can see it here: {0}".format(py3pin_link.format(id)))
        elif "board" in job:
            create_board(name=job["board"]["name"],
                        description=job["board"]["description"],
                        category=job["board"]["category"],
                        privacy=job["board"]["privacy"],
                        layout=job["board"]["layout"])
        elif "section" in job:
            create_board_section(board_id=job["pin"]["board_id"],
                        section_name=job["section"]["section_name"])

        job_queue.pop(0)

        # We would go back one since we just removed an item from the list.
        # In this case, we don't have to, because we are *always* going to pop an item from the list.
        # We can just pop 0 until we empty the list or reach the original max

        x+=1
        print("Job {0}/{1} Done.".format(x, org_max))

        if job_max == 0:
            break

        job_max-=1

    if org_max > 0:
        print("\nJobs completed. Jobs up for retry: {0}/{1}".format(len(job_queue), org_max))

# Scrape the url for specific data to fill out the entry for the user
def scrape_data(url):
    # Check to see if the url is a valid link, among other things, like checking to see if it is a google drive link. Ew
    foo, reason = is_url_valid(url)

    data = {}

    if foo:
        # If the url is permitable, scrape the page for DAAATA
        data, foo = scrape_page(url)

    return data, foo, reason

def scrape_page(url):
    data = {}
    status = True

    title = None
    desc = None
    studio = None
    price = None
    currency = None
    img_link = None


    steamapps_form = "https://store.steampowered.com/api/appdetails?appids={}"
    gamejolt_form = "https://gamejolt.com/site-api/web/discover/games/{}"
    #googleplay_form = "https://play.google.com/store/apps/details?id={}" -- Unnecessary since we use dedicated library

    if "store.steam" in url:
        app_id = search("app/{}/", url).fixed[0]
        url = steamapps_form.format(app_id)
    elif "gamejolt.com" in url:
        # Get app ID from end of gamejolt link. Have to add "url[-1]" to actually give it the last digit.
        app_id = url[url.rfind("/")+1:-1] + url[-1]
        url = gamejolt_form.format(app_id)
    elif "play.google" in url:
        # Find the app ID in the url
        app_id = url[url.find("=com")+1:]

        # Fetch the details using the play-scraper python library
        # This library is a god-send. It is fast, accurate, and gives you more information than you need
        app = play_scraper.details(app_id)

        data["title"] = app["title"]
        data["desc"] = app["description"]
        data["studio"] = app["developer"]
        data["price"] = app["price"]
        data["currency"] = get_currency_type(app["price"])
        data["img_link"] = app["screenshots"][0]

        # Since we have all the data we need through play-scraper, end the function and return the data and status = true
        return data, True

    # Grab the page content
    html = str(requests.get(url).content)

    # -- Use this to write to file the example HTML.
    # -- Had some weird differences between pre-javascript Chrome and Requests library HTML at times, which made it hard to format the scraping
    #
    # with open("whatamiseeing.txt", "w+") as f:
    #     soup = BeautifulSoup(html, 'lxml')
    #     f.write(soup.prettify())

    # Format the scraping parameters for individual publishing sites
    if "itch.io" in url:
        title_param='class="game_title">{}</h1>'
        desc_param=',"description":"{}"'
        studio_param='Follow {}<'
        price_param='"actual_price":{},'
        img_param='name="twitter:card"/><meta content="{}"'
    elif "store.steampowered" in url:
        title_param='"game","name":"{}"'
        desc_param='"short_description":"{}"'
        studio_param='"developers":["{}"<'
        price_param='discount_original_price\\">{}<\/span>'
        img_param='"header_image":"{}"'

        if not search(price_param, html):
            price_param='"final_formatted":"{}"'
    elif "gamejolt.com" in url:
        title_param='"title":"{}"'
        desc_param=None # Getting the description through Gamejolt's web API is a pain in the dark crevice
        studio_param='"Developer","username":"{}"'
        price_param='"pricings":[{"id":{},"amount":{},'
        img_param='"img_thumbnail":"{}"'

    # Go through each parameter and check whether or not it was set
    # If it was, try using the parse library and search for the given format
    # If found, set the related value to what was found
    if title_param:
        try:
            title = search(title_param, html).fixed[0]
        except:
            pass

    if desc_param:
        try:
            desc = search(desc_param, html).fixed[0]

            desc = strip_html_tags(desc)
        except:
            pass
    else:
        # Gamejolt's web api provides a pretty muddy description value,
        # so it is easier/only possible to look for the first value match and then grab all the text until the next value match
        if "gamejolt.com" in url:
            pos = html.find('"text')+1
            pos = html.find('"text', pos)+12
            pos2 = html.find('\\"}]}', pos)-1

            desc = html[pos:pos2]

            # The description values can change drastically. I would go above and beyond, but Gamejolt's desc return value is a loose cannon
            # This checks to see if ("text") is still in the description. If it is, the value we got is not clean and we need a new one from the user
            if '"text' in desc:
                desc = None

    if studio_param:
        try:
            studio = search(studio_param, html).fixed[0]
        except:
            pass

    if price_param:
        try:
            price = search(price_param, html).fixed[0]

            price = costify(price)
        except:
            # It may except because Gamejolt lists prices a little weirdly. The format completely changes when the game is free
            if "gamejolt.com" in url:
                if "pricings" in html:
                    price = "Free"
                else:
                    pass

    if img_param:
        try:
            img_link = search(img_param, html).fixed[0]

            img_link = img_link.replace("\\", "")
        except:
            pass

    if not title or not desc or not studio or not price or not currency or not img_link:
        status = False

    if price:
        if price == "0":
            price = "Free"

    currency = get_currency_type(price)

    data["title"] = title
    data["desc"] = desc
    data["studio"] = studio
    data["price"] = price
    data["currency"] = currency
    data["img_link"] = img_link
        

    return data, status


def strip_html_tags(txt):
    clean_txt = re.sub(r'<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});', "", txt)

    clean_txt = clean_txt.replace("\\", "")
    clean_txt = clean_txt.replace("xc2", "")
    clean_txt = clean_txt.replace("xae", "")
    clean_txt = clean_txt.replace("u2019", "'")


    return clean_txt

def costify(txt):
    # If price is 0, set to Free.
    # If price is free, set to Free.
    if txt == "0":
        txt = "Free"
    elif "free" in txt.lower():
        txt = "Free"

    # Try statement is a just in case. Shouldn't ever trigger, but hey, now it's going to happen just because I said that
    try:
        # If not Free and if it does not have a decimal point (like 199 instead of 1.99), add it
        if "Free" not in txt:
            if "." not in txt:
                txt = txt[0:-2] + "." + txt[-2:-1] + txt[-1]
    except:
        print("\nFailed to add decimal point to price. Assuming price {0} was supposed to be 'Free', but wasn't caught in if statement.\n".format(txt))

    return txt

# Test message to see if it has invalid characters that will cause errors
def is_message_valid(message):
    test = False

    try:
        with open("test_(should_be_removed).txt", "w+") as f:
            f.write(message.content)
            test = True
    except: test = False

    os.remove("test_(should_be_removed).txt")

    return test

# Check to see if we should do something with this message, and, if so, get what channel type it is from
def is_msg_for_me(msg):
    # If this is a direct message, update the entry and break the function. We don't need to do anything else
    if msg.direct:
        return True, None

    # If msg is in our connected servers
    if msg.server_id in server_data:
        # if msg is in the entry channel of that server
        if server_data[msg.server_id].entry:
            if msg.channel_id in server_data[msg.server_id].entry:
                return True, server_info.entry
        # if msg is in the promo channel of that server
        if server_data[msg.server_id].promo:
            if msg.channel_id in server_data[msg.server_id].promo:
                return True, server_info.promo
    
    # If we made it here, this msg is not for us
    return False, None

# Perform some checks on the URL
def is_url_valid(url):
    url = url.lower()
    if "discord.gg" in url and "invite" in url:
        return False, "Discord server invite links are not permitted"
    elif "drive.google" in url:
        return False, "Google Drive links are not permitted"
    elif "instagram.com" in url or "twitter.com" in url or "facebook.com" in url or "reddit.com" in url or "tumblr.com" in url:
        return False, "Social Media links are not permitted"

    try:
        request = requests.get(url)
        if request.status_code != 200:
            return False, "Could not load the link"
    except:
        return False, "Could not load the link"

    return True, None

# Check to see if the given text contains a currency symbol and return it if so
def get_currency_type(txt):
    syb = None

    for s in currency_symbols:
        if s in txt:
            syb = s
            return syb

    return syb

# Go through the list of server members and find the administrator of the server
def get_owner(server):
    for user in server.members:
        if user.server_permissions.administrator:
            return user

    return None

# See if a user is in a mutual server and return what mutual server(s) they are from
def get_user_mutuals(user_id):
    mutuals = []

    for server in servers:
        for user in server.members:
            if user.id == user_id:
                mutuals.append(server)
                break

    if len(mutuals) < 1:
        return None
    else:
        return mutuals

# Get the server the user owns, checking the given input to see if they included an ID. Otherwise, check through mutuals to see if they own any
# Shortcut if we are already speaking in a server
# Also return number of owned servers and filtered input
def get_user_owned_servers(msg, input = ("None")):
    given_id = None

    # Input will come as a tuple, so we make it a list to make it mutable
    input = list(input)

    # A simple check to see if the first argument is a server ID
    if input[0].isdigit():
        if bot.get_server(input[0]):
            given_id = input[0]
            input.pop(0)

    # Shortcut if the msg is not in a private channel, we weren't given an ID, and the user is the owner of the server in question
    if not msg.direct:
        if not given_id:
            if get_owner(bot.get_server(msg.server_id)).id == msg.author_id:
                return [bot.get_server(msg.server_id)], 1, input

    # Get the servers that the user and bot are both in
    mutual_servers = get_user_mutuals(msg.author_id)

    # If given server id, check to see if user is an admin of that server
    # Else, check each one to see if the user is an admin of any of them
    servers_owned = []
    num_owned = 0

    if given_id:
        if get_owner(bot.get_server(given_id)).id == msg.author_id:
            servers_owned.append(bot.get_server(given_id))
            num_owned = 1
    else:
        for ser in mutual_servers:
            if get_owner(bot.get_server(ser.id)).id == msg.author_id:
                num_owned += 1
                servers_owned.append(bot.get_server(ser.id))

    # Set server_owned to none if it doesn't have anything in it. Makes it cleaner to check later
    if len(servers_owned) == 0:
        servers_owned = None

    return servers_owned, num_owned, input

# Go through list and return the position of the first null value
def get_first_null_value(list):
    x = 0
    for y in list:
        if y is None:
            return x
        x += 1
    
    return x

# Get the string list of the given server's sections
# This is for the second to last stage question
def get_section_list_string(server_id):
    sections_str = ""
    x = 0

    for section_name in server_data[server_id].sections:
        sections_str += "\n`{0}` - **{1}**".format(x, section_name)
        x += 1

    if sections_str is "":
        sections_str = None

    return sections_str

# Get this server's section by number
# Used when user responds with what section they would like their entry placed in
def get_section_id(server_id, given_list, num):
    
    filter = "`" + num + "` - **{}**"

    section_name = search(filter, given_list).fixed[0]

    if section_name:
        return server_data[server_id].sections[section_name]

    return None

# Get the ID of whatever Pinterest resource we get
def get_py3pin_id(response):
    data = json.loads(response)

    id = data["resource_response"]["id"]

    return id

# Check to see if a user is in the entry queue
def is_user_in_queue(author_id):
    if author_id in user_queue:
        return True

    return False


# Check to see if this message contains a command
def is_command(msg):
    if msg.content.lower() in command_list:
        return True

    return False

def upload_pin(discord_user="",
                board_id='',
                section_id=None,
                image_url='my_imag.png',
                description='this is auto pin',
                title='a bot did this',
                link='https://www.google.com/'):

    status = True
    pin = None

    try:
        pin = pinterest.pin(board_id=board_id, section_id=section_id, image_url=image_url,
                                    description=description, title=title, link=link)

        jason = json.loads(pin.content)
        id = jason["resource_response"]["data"]["id"]
    except Exception as e:
        if "401" in str(e) or "403" in str(e):
            try:
                pinterest.login()
            except Exception as e:
                print("\n**FAILED TO LOGIN TO PINTEREST AFTER EXCEPTION**:\n--\n{0}\n--".format(str(e)))
        status = False

        add_job("pin", discord_user=discord_user, board_id=board_id, section_id=section_id, title=title, description=description,
                link=link, image_url=image_url)
    return status, id

def create_board(server_id='',
                name='',
                description='',
                # film_music_books is the value for the "Entertainment" category in Pinterest
                category='film_music_books',
                privacy='public',
                layout='default'):

    global new_boards
    new_boards+=1

    status = True

    try:
        response = pinterest.create_board(name=name, description=description, category=category,
                                privacy=privacy, layout=layout)

        jason = json.loads(response.content)
        id = jason["resource_response"]["data"]["id"]

        server_data[server_id].board = id
    except Exception as e:
        if "401" in str(e) or "403" in str(e):
            try:
                pinterest.login()
            except Exception as e:
                print("\n**FAILED TO LOGIN TO PINTEREST AFTER EXCEPTION**:\n--\n{0}\n--".format(str(e)))
        status = False

        add_job("board", server_id=server_id, board_id=None, name=name, description=description, category=category, privacy=privacy, layout=layout)
    return status


def create_board_section(server_id='', board_id='', section_name=''):
    global new_sections
    new_sections+=1

    status = True

    try:
        response = pinterest.create_board_section(board_id=board_id, section_name=section_name)
        jason = json.loads(response.content)
        id = jason["resource_response"]["data"]["id"]

        server_data[server_id].sections[section_name] = id
    except Exception as e:
        if "401" in str(e) or "403" in str(e):
            try:
                pinterest.login()
            except Exception as e:
                print("\n**FAILED TO LOGIN TO PINTEREST AFTER EXCEPTION**:\n--\n{0}\n--".format(str(e)))
        status = False

        add_job("section", server_id=server_id, board_id=board_id, section_name=section_name)
    return status

# Add a job to the job queue. Jobs are necessary in case we hit Pinterest's rate limit.
def add_job(job_type="",
            discord_user=None,
            server_id=None,
            board_id=None,
            section_id=None,
            section_name=None,
            name=None,
            title=None,
            description=None,
            link=None,
            image_url=None,
            category=None,
            privacy=None,
            layout=None):

    if job_type is "pin":
        job_queue.append(
            {
                "pin": {
                    "discord_user": discord_user,
                    "board_id": board_id,
                    "section_id": section_id,
                    "section_name": section_name,
                    "name": name,
                    "title": title,
                    "description": description,
                    "link": link,
                    "image_url": image_url,
                    "category": category,
                    "privacy": privacy,
                    "layout": layout
                }
            }
        )
    elif job_type is "board":
        job_queue.append(
            {
                "board": {
                    "server_id": server_id,
                    "board_id": board_id,
                    "section_id": section_id,
                    "section_name": section_name,
                    "name": name,
                    "title": title,
                    "description": description,
                    "link": link,
                    "image_url": image_url,
                    "category": category,
                    "privacy": privacy,
                    "layout": layout
                }
            }
        )
    elif job_type is "section":
        job_queue.append(
            {
                "section": {
                    "server_id": server_id,
                    "board_id": board_id,
                    "section_id": section_id,
                    "section_name": section_name,
                    "name": name,
                    "title": title,
                    "description": description,
                    "link": link,
                    "image_url": image_url,
                    "category": category,
                    "privacy": privacy,
                    "layout": layout
                }
            }
        )

    print("\nJob type: {0} added.\n".format(job_type))

if __name__ == '__main__':
    main()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(do_jobs, 'interval', minutes=30)
    scheduler.start()

bot.run(BOT_TOKEN)