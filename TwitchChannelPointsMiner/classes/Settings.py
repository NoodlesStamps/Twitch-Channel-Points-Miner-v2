from enum import Enum, auto


class Priority(Enum):
    ORDER = auto()
    STREAK = auto()
    DROPS = auto()
    SUBSCRIBED = auto()
    POINTS_ASCENDING = auto()
    POINTS_DESCENDING = auto()


class FollowersOrder(Enum):
    ASC = auto()
    DESC = auto()

    def __str__(self):
        return self.name


# Empty object shared between class
class Settings(object):
    __slots__ = ["logger", "streamer_settings",
                 "enable_analytics", "disable_ssl_cert_verification", "disable_at_in_nickname",
                 "auto_select_strategy", "auto_select_strategy_days", "auto_selected_strategy_override", "log_file_path"]

# Initialize static members for Settings
Settings.auto_select_strategy = False
Settings.auto_select_strategy_days = 7
Settings.auto_selected_strategy_override = None
Settings.log_file_path = None

class Events(Enum):
    STREAMER_ONLINE = auto()
    STREAMER_OFFLINE = auto()
    GAIN_FOR_RAID = auto()
    GAIN_FOR_CLAIM = auto()
    GAIN_FOR_WATCH = auto()
    GAIN_FOR_WATCH_STREAK = auto()
    BET_WIN = auto()
    BET_LOSE = auto()
    BET_REFUND = auto()
    BET_FILTERS = auto()
    BET_GENERAL = auto()
    BET_FAILED = auto()
    BET_START = auto()
    BONUS_CLAIM = auto()
    MOMENT_CLAIM = auto()
    JOIN_RAID = auto()
    DROP_CLAIM = auto()
    DROP_STATUS = auto()
    CHAT_MENTION = auto()

    def __str__(self):
        return self.name

    @classmethod
    def get(cls, key):
        return getattr(cls, str(key)) if str(key) in dir(cls) else None
