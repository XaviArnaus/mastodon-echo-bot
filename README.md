# Mastodon Echo bot
I am a bot for Mastodon instances that publishes content from 3 different sources:
* RSS feeds
* Other Mastodon accounts
* Twitter accounts

What features do I provide?
* **Super detailed setup via a config file**: Take full control of the execution
* **No DB is needed**: Everything is done with files
* **Anti-flood publishing**: Publish one post in every execution following a queue
* **Keyword filtering**: Filter out posts from Mastodon or RSS Feeds that do not contain a set of words 
* **Images supported**: Also publish the images that come with the original post.
* **Exhaustive logging**: Log everything that is happening while executing, so you can monitor what's going on
* **Dry Run support**: You can set it up and run it without any actual publishing until you're happy with the result
* **Keep track of what is already captured**: To avoid repeating published posts!

# Explain me more
This bot is made with ❤️ from Düsseldorf and It is designed to capture specific content from defined sources and publish it through a single bot account in Mastodon in a localized and topic specific instance.

## Configuration File
It is a Yaml that contains all the possible options, feeds and Mastodon & Twitter accounts to follow. All options come commented.
* Make sure you create your execution copy from [the example shipped](./config.yaml.dist): it has to be called `config.yaml`

## No DB is needed
Why to use an infrastructure that not necessarily comes for granted when everything can be achieved with files? This way you can easily monitor and adjust anyting quickly.

## Anti-flood publishing: be kind
The bot is meant to be executed scheduled through a cron every 15 or 30 minutes. In every run it gathers posts into a queue and is intended to publish only one re-toot, the older first.

Why? The idea is to avoid flooding, having a large amount of posts coming out of nowhere. Be kind with your neighbours in your instance :-)

You can change this behaviour from [the config file](./config.yaml.dist#L109) and simply publish everything queued in every run.

## Keyword Filtering
This allows you to filter out all content that does not contain any of the specified words.
It works as per *filtering profiles*, defining a profile only once that contains all the words to analyse, and applying this profile to the RSS feeds and Mastodon accounts.

Create a profile in [this section of the config file](./config.yaml.dist#L111) and define then the profile to be used [in your feed](./config.yaml.dist#L74) or [your Mastodon setup](./config.yaml.dist#L53).

The Twitter accounts are still not covered by this feature.

## Images support
The images that come with the Mastodon, Twitter and RSS posts can bring images, that will be downloaded and re-upload to the published post, preserving any description that they could have

## Exhaustive logging
A bot is somethig that executes in loneliness, so it's cool to have the work logged into a file with several logging degrees so that we can monitor how is it behaving. In [the config file](./config.yaml.dist#L16) one can also make it display the log while running for these debugging situations.

## Dry Run
When setting up the bot you may want to avoid to publish the queue, while you're adjusting the parameters. With this Dry Run option it can run and gather content and fill the queues without the fear of flooding your Mastodon account with test messages. [Here in the config file](./config.yaml.dist#L106) you can control this option, that **comes activated by default**!

## Keep track of what is already captured
The bot registers every new contentn in every run, so that it avoids repeating the actions over the same items. This is useful as some sources mark an old post as new and other bots may re-publish it. 
As usual this can be turned off and repeat all processing for every content in every run, useful while developing. 

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
4. Discover which is the python3 binary your host is using. This bot uses `python3` to run, and if it's not your case, you'll have to update the reference at the top of the `Makefile` file.
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
    * storage/media/
10. Create the app, this is done just one time to get the credentials
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
