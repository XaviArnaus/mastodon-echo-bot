# Mastodon Echo bot
I am a bot that spies the registered accounts for his/her/its reblogs.

The assumtion is that these accounts would have curated these re-toots and therefor they are good content.

Once these toots are collected into a queue, the bot will re-toot them.

## Why is this useful?
I have an account in one server, where I enjoy my time and do not intend to leave. I do re-toot for what I find interesting therefor I am actually curating content on-the go.

Now I open a new server where there is yet no content and no live. The only way to get the Federation timeline alive is by having interactions, so I have this bot to have the new server building relationships with other severs and other accounts.

## Re-toot kindly
The bot is meant to be executed scheduled through a cron every 15 or 30 minutes. In every run it gathers toots into a queue and is intended to publish only one re-toot, the older of the list.

Why? Ide idea is to avoid having a large amount of re-toots coming out of nowhere. Humans that care about content usually do not re-toot so often, letting the bot time to catch up with the queue.

You can of course change this behaviour from the config file and simply publish everything in every run.

# Installation
As this is a bot that connects as an app to a given Mastodon server, it can be deployed anywhere with an internet connection, from a hosting to a Raspberry Pi.

## Requirements
* Access to a machine with shell console and internet access
    * Ideally with the ability to set up crontab entries
* Python 3
    * Did not try it with Python 2.7
* Access to a Mastodon server where a new account can be created
    * Unless you intend to reuse an existing account.

## Set up

### In the Mastodon server
1. Create yourself a new Mastodon account in a server of your preference.
2. Set up this account as a bot
3. Create an app in this account, under the Development section in your Preferences.

### In the host
1. Start a shell console in the host that will allocate the bot
2. Move yourself to the location that will allocate the folder of the bot
3. Clone this repository
```
$ git clone git@github.com:XaviArnaus/mastodon-echo-bot.git
```
4. Discover which is the python3 binary your host is using. In case it is `python3` and not `python`, you'll have to update the reference at the top of the `Makefile` file.
5. Ensure that your system has `pip`. Otherwise install it. i.e. for Debian:
```
$ sudo apt install pip
```
6. Move into the app folder and install the dependencies
```
$ cd mastodon-echo-bot
$ make init
```
7. Generate your own config file from the one distributed in the repo
```
$ cp config.yaml.dist config.yaml
```
8. Edit the config file and adjust it to your needs
9. Make sure you (the user that will use run the bot) has write permission to the following folders:
    * root of the app
    * log/
    * storage/
10. Create the app, this is done just one time
```
$ make create_app
```

An now you're ready to run the bot.

# Running the bot
## Just one time
To run the bot just one time simply execute the following command:
```
make run
```

## Run scheduled
To run it every `x` time simply add it into the crontab of your host.
1. Start a shell console tot he host that allocates the bot
2. Move to the directory that holds your bot and show the full path
```
$ cd ~/bots/mastodon-echo-bot
$ pwd
```
Copy the path that appears there!

3. Edit the `crontab`
```
$ crontab -e
```
4. Add the following line for executing every 15 minutes. Use the path you copied in the step 2 and also add the `make run` command:
```
0,15,30,45 * * * * /local/mastodon/bots/mastodon-echo-bot/make run
```

## Dry Run
Keep in mind that you can set up the config file so that the run **will not** publish anything, but will do almost all action, so you can follow the run from the log file.
