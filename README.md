![Logo](/gameboard.png)
![Demo](/demo.png)
![Pin Demo](/pindemo.png)

# Gameboard
A Discord bot that lists games to Pinterest

## Discord Invite

Use this [invite](https://discordapp.com/oauth2/authorize?client_id=658509820957032458&permissions=10240&scope=bot) to invite the bot to your server.

## Hosting

If you wish to host the bot yourself, feel free to do so. It requires Python 3+. You will need to create a Pinterest account and enter the details into `credentials.txt`, as well as your bot's token. However, do not claim it is your own work, and leave in the credits.

## Setup

Upon joining your server, it will message the owner of the server with details to set it up. It is just a few commands that will take only a few moments: `setentry` `setpromo` and `addsection`

## Commands

Unless otherwise stated, the callsign/prefix for commands is: `g>`

`(parameter)` - Optional parameter

`<parameter>` - Required parameter

Administrative commands:

### Setentry

`setentry (server_id) <channel_id>` sets the entry channel for the server. This is the channel that you want entries to be made in. Most servers will likely set this to "bot" or "bot-spam".

### Setpromo

`setpromo (server_id) <channel_id>` sets the promotion channel for the server. This is the channel that members can promote their games and stuff in. Most servers will likely have this named "promo".

### Addsection

`addsection (server_id) <Section Name...>` adds a section to this server's board. Sections can be configured as you wish. It only matters how you want to segment the entries that members make. For instance, you can add just one section named "Community Games" and all games will only be able to be placed under that, or you can make sections for different events like "Ludum Dare 41", "Community Jam 69", or you could even create seperate sections for genres like "Strategy", "Puzzle", or "Mobile". It is completely up to you. Just keep in mind that, for the time being, sections cannot be deleted.

Member-level commands:

### Entry

`entry` starts the entry process for adding a project to Gameboard.

### Board

`board` retrieves the link to this community's board on Pinterest.

### Help

`help` display member-level commands

### What

`what` provides a description of the bot, some of its history, and who made it.

