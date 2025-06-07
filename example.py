# -*- coding: utf-8 -*-

import logging
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.Webhook import Webhook
from TwitchChannelPointsMiner.classes.Telegram import Telegram
from TwitchChannelPointsMiner.classes.Matrix import Matrix
from TwitchChannelPointsMiner.classes.Pushover import Pushover
from TwitchChannelPointsMiner.classes.Gotify import Gotify
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import (
    Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode, KellyProbabilitySource
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

# Example of setting up default BetSettings with Kelly Criterion
# Note: The BetSettings().default() method already sets defaults for kelly_fraction (0.5)
# and kelly_probability_source (ODDS_PERCENTAGE) if they are None when strategy is KELLY_CRITERION.
# This explicit configuration is for clarity or if you want different defaults.
default_kelly_bet_settings = BetSettings(
    strategy=Strategy.KELLY_CRITERION,
    max_points=25000,                # Max points to use for a single bet
    minimum_points=100,              # Minimum points for a bet

    # Kelly Criterion specific settings:
    kelly_fraction=0.3,              # Use 30% of the calculated Kelly stake (e.g., 0.1 for 10%, 1.0 for full Kelly)
    kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE, # Or KellyProbabilitySource.USER_PERCENTAGE

    # Common settings (delay might still be relevant)
    delay_mode=DelayMode.FROM_END,
    delay=10
    # percentage and percentage_gap are not used by Kelly Criterion but have defaults if you switch strategy
)

default_streamer_settings_config = StreamerSettings(
    make_predictions=True,
    follow_raid=True,
    claim_drops=True,
    claim_moments=True,
    watch_streak=True,
    community_goals=False,
    chat=ChatPresence.ONLINE,
    bet=default_kelly_bet_settings # Assign the BetSettings object here
)

twitch_miner = TwitchChannelPointsMiner(
    username="your-twitch-username",
    password="write-your-secure-psw",           # If no password will be provided, the script will ask interactively
    claim_drops_startup=False,                  # If you want to auto claim all drops from Twitch inventory on the startup
    auto_select_strategy=True,                  # Enable automatic strategy selection
    auto_select_strategy_days=7,                # Use last 7 days of logs for auto-selection
    priority=[                                  # Custom priority in this case for example:
        Priority.STREAK,                        # - We want first of all to catch all watch streak from all streamers
        Priority.DROPS,                         # - When we don't have anymore watch streak to catch, wait until all drops are collected over the streamers
        Priority.ORDER                          # - When we have all of the drops claimed and no watch-streak available, use the order priority (POINTS_ASCENDING, POINTS_DESCENDING)
    ],
    enable_analytics=False,                     # Disables Analytics if False. Disabling it significantly reduces memory consumption
    disable_ssl_cert_verification=False,        # Set to True at your own risk and only to fix SSL: CERTIFICATE_VERIFY_FAILED error
    disable_at_in_nickname=False,               # Set to True if you want to check for your nickname mentions in the chat even without @ sign
    logger_settings=LoggerSettings(
        save=True,                              # If you want to save logs in a file (suggested)
        console_level=logging.INFO,             # Level of logs - use logging.DEBUG for more info
        console_username=False,                 # Adds a username to every console log line if True. Also adds it to Telegram, Discord, etc. Useful when you have several accounts
        auto_clear=True,                        # Create a file rotation handler with interval = 1D and backupCount = 7 if True (default)
        time_zone="",                           # Set a specific time zone for console and file loggers. Use tz database names. Example: "America/Denver"
        file_level=logging.DEBUG,               # Level of logs - If you think the log file it's too big, use logging.INFO
        emoji=True,                             # On Windows, we have a problem printing emoji. Set to false if you have a problem
        less=False,                             # If you think that the logs are too verbose, set this to True
        colored=True,                           # If you want to print colored text
        color_palette=ColorPalette(             # You can also create a custom palette color (for the common message).
            STREAMER_online="GREEN",            # Don't worry about lower/upper case. The script will parse all the values.
            streamer_offline="red",             # Read more in README.md
            BET_wiN=Fore.MAGENTA                # Color allowed are: [BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET].
        ),
        telegram=Telegram(                                                          # You can omit or set to None if you don't want to receive updates on Telegram
            chat_id=123456789,                                                      # Chat ID to send messages @getmyid_bot
            token="123456789:shfuihreuifheuifhiu34578347",                          # Telegram API token @BotFather
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],                          # Only these events will be sent to the chat
            disable_notification=True,                                              # Revoke the notification (sound/vibration)
        ),
        discord=Discord(
            webhook_api="https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J",  # Discord Webhook URL
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],                                  # Only these events will be sent to the chat
        ),
        webhook=Webhook(
            endpoint="https://example.com/webhook",                                                                    # Webhook URL
            method="GET",                                                                   # GET or POST
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],                                  # Only these events will be sent to the endpoint
        ),
        matrix=Matrix(
            username="twitch_miner",                                                   # Matrix username (without homeserver)
            password="...",                                                            # Matrix password
            homeserver="matrix.org",                                                   # Matrix homeserver
            room_id="...",                                                             # Room ID
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, Events.BET_LOSE], # Only these events will be sent
        ),
        pushover=Pushover(
            userkey="YOUR-ACCOUNT-TOKEN",                                             # Login to https://pushover.net/, the user token is on the main page
            token="YOUR-APPLICATION-TOKEN",                                           # Create a application on the website, and use the token shown in your application
            priority=0,                                                               # Read more about priority here: https://pushover.net/api#priority
            sound="pushover",                                                         # A list of sounds can be found here: https://pushover.net/api#sounds
            events=[Events.CHAT_MENTION, Events.DROP_CLAIM],                          # Only these events will be sent
        ),
        gotify=Gotify(
            endpoint="https://example.com/message?token=TOKEN",
            priority=8,
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION], 
        )
    ),
    streamer_settings=default_streamer_settings_config # Pass the configured default StreamerSettings
)

# You can customize the settings for each streamer. If not settings were provided, the script would use the streamer_settings from TwitchChannelPointsMiner.
# If no streamer_settings are provided in TwitchChannelPointsMiner the script will use default settings.
# The streamers array can be a String -> username or Streamer instance.

# The settings priority are: settings in mine function, settings in TwitchChannelPointsMiner instance, default settings.
# For example, if in the mine function you don't provide any value for 'make_prediction' but you have set it on TwitchChannelPointsMiner instance, the script will take the value from here.
# If you haven't set any value even in the instance the default one will be used

#twitch_miner.analytics(host="127.0.0.1", port=5000, refresh=5, days_ago=7)   # Start the Analytics web-server

twitch_miner.mine(
    [
        Streamer("streamer-username01", settings=StreamerSettings(make_predictions=True, follow_raid=False, claim_drops=True, watch_streak=True, community_goals=False, bet=BetSettings(strategy=Strategy.SMART, percentage=5, stealth_mode=True,  percentage_gap=20, max_points=234, filter_condition=FilterCondition(by=OutcomeKeys.TOTAL_USERS, where=Condition.LTE, value=800 ) ) )),
        # Example of a specific streamer using Kelly Criterion with different settings
        # Streamer(
        #     "another-streamer",
        #     settings=StreamerSettings(
        #         make_predictions=True,
        #         bet=BetSettings(
        #             strategy=Strategy.KELLY_CRITERION,
        #             max_points=10000,
        #             kelly_fraction=0.25, # A more conservative Kelly fraction
        #             kelly_probability_source=KellyProbabilitySource.USER_PERCENTAGE,
        #             minimum_points=50,
        #             delay_mode=DelayMode.FROM_START,
        #             delay=5
        #         )
        #         # other settings for this streamer like claim_drops, watch_streak etc. can be added here
        #     )
        # ),
        Streamer("streamer-username02", settings=StreamerSettings(make_predictions=False, follow_raid=True, claim_drops=False, bet=BetSettings(strategy=Strategy.PERCENTAGE, percentage=5, stealth_mode=False, percentage_gap=20, max_points=1234, filter_condition=FilterCondition(by=OutcomeKeys.TOTAL_POINTS, where=Condition.GTE, value=250 ) ) )),
        Streamer("streamer-username03", settings=StreamerSettings(make_predictions=True, follow_raid=False, watch_streak=True, community_goals=True, bet=BetSettings(strategy=Strategy.SMART, percentage=5, stealth_mode=False, percentage_gap=30, max_points=50000, filter_condition=FilterCondition(by=OutcomeKeys.ODDS, where=Condition.LT,  value=300 ) ) )),
        Streamer("streamer-username04", settings=StreamerSettings(make_predictions=False, follow_raid=True, watch_streak=True)),
        Streamer("streamer-username05", settings=StreamerSettings(make_predictions=True, follow_raid=True, claim_drops=True, watch_streak=True, community_goals=True, bet=BetSettings(strategy=Strategy.HIGH_ODDS, percentage=7, stealth_mode=True,  percentage_gap=20, max_points=90, filter_condition=FilterCondition(by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GTE, value=300 ) ) )),
        Streamer("streamer-username06"), # Will use default_streamer_settings_config (Kelly Criterion)
        Streamer("streamer-username07"), # Will use default_streamer_settings_config (Kelly Criterion)
        Streamer("streamer-username08"), # Will use default_streamer_settings_config (Kelly Criterion)
        "streamer-username09",           # Will use default_streamer_settings_config (Kelly Criterion)
        "streamer-username10",          # Will use default_streamer_settings_config (Kelly Criterion)
        "streamer-username11"           # Will use default_streamer_settings_config (Kelly Criterion)
    ],                                  # Array of streamers (order = priority)
    followers=False,                    # Automatic download the list of your followers
    followers_order=FollowersOrder.ASC  # Sort the followers list by follow date. ASC or DESC
)
