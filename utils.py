from datetime import datetime
import logging
from dateutil import parser
import pytz

logger = logging.getLogger(__name__)

def parse_date(date_str):
    """Parses date string to datetime object"""
    try:
        return parser.parse(date_str)
    except Exception as e:
        logger.error(f"Error parsing date {date_str}: {str(e)}")
        return None

def format_date(date_str, target_timezone=None):
    """
    Formats date string to a consistent format with timezone conversion
    If target_timezone is provided, converts the time to that timezone
    """
    try:
        # Parse the date string
        date_obj = parse_date(date_str)
        if not date_obj:
            return date_str

        # If date_obj doesn't have timezone info, assume UTC
        if date_obj.tzinfo is None:
            date_obj = pytz.UTC.localize(date_obj)

        # Convert to target timezone if specified
        if target_timezone:
            try:
                target_tz = pytz.timezone(target_timezone)
                date_obj = date_obj.astimezone(target_tz)
                return date_obj.strftime('%B %d, %Y %H:%M %Z')
            except Exception as e:
                logger.error(f"Error converting timezone: {str(e)}")
                return date_obj.strftime('%B %d, %Y %H:%M UTC')

        return date_obj.strftime('%B %d, %Y %H:%M UTC')
    except ValueError as e:
        logger.error(f"Error formatting date: {str(e)}")
        return date_str

def format_hackathon_message(hackathon, target_timezone=None):
    """Formats hackathon information for Discord message with timezone support"""
    date_str = format_date(hackathon['date'], target_timezone)

    return (
        f"**{hackathon['title']}**\n"
        f"Platform: {hackathon['platform']}\n"
        f"Date: {date_str}\n"
        f"Link: {hackathon['link']}\n"
        f"-------------------"
    )

def get_common_timezones():
    """Returns a list of common timezone names"""
    return [
        'US/Pacific', 'US/Mountain', 'US/Central', 'US/Eastern',
        'Europe/London', 'Europe/Paris', 'Europe/Berlin',
        'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
        'Australia/Sydney', 'Pacific/Auckland'
    ]