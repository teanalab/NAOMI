from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Use New York timezone (auto-DST) for “Eastern”
EASTERN_TZ = ZoneInfo("America/New_York")

def get_current_eastern():
    """
    Returns a tuple:
      - datetime object in Eastern Time (New York) timezone
      - formatted string "YYYY-MM-DD HH:MM:SS"
    """
    now_utc = datetime.now(timezone.utc)
    now_e = now_utc.astimezone(EASTERN_TZ)
    return now_e, now_e.strftime("%Y-%m-%d %H:%M:%S")

def get_eastern_prefix():
    """
    Returns a filename-safe prefix in Eastern Time, e.g. "Sep17_16-45"
    """
    now_e, _ = get_current_eastern()
    return now_e.strftime("%b%d_%H-%M")


# NEW: format any epoch timestamp into Eastern string
def format_eastern_from_timestamp(ts: float, datefmt: str | None = None) -> str:
    dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    dt_e = dt_utc.astimezone(EASTERN_TZ)
    return dt_e.strftime(datefmt) if datefmt else dt_e.isoformat()
