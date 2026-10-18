"""Calendar ranges and bucket boundaries in the configured report timezone."""
import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LEVELS=('day','week','month','quarter','halfyear','year')
MONTHS={'month':1,'quarter':3,'halfyear':6,'year':12}
DEFAULT_TIMEZONE='Asia/Singapore'
DEFAULT_DAY_START_HOUR=9


def local(value, zone):
    value=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if value.tzinfo is None:
        value=value.replace(tzinfo=ZoneInfo(zone))
    return value.astimezone(ZoneInfo(zone))


def shift_month(value, count):
    index=value.year*12+value.month-1+count
    year,month=divmod(index,12);month+=1
    return value.replace(year=year,month=month,day=min(value.day,calendar.monthrange(year,month)[1]))


def bounds(level, anchor, zone=DEFAULT_TIMEZONE, day_start_hour=DEFAULT_DAY_START_HOUR):
    start=local(anchor,zone).replace(hour=day_start_hour,minute=0,second=0,microsecond=0)
    if level=='day':end=start+timedelta(days=1)
    elif level=='week':
        start-=timedelta(days=start.weekday());end=start+timedelta(days=7)
    else:
        count=MONTHS[level]
        start=start.replace(month=((start.month-1)//count)*count+1,day=1)
        end=shift_month(start,count)
    return start.isoformat(),end.isoformat()


def previous(start, end, level, zone):
    start,end=local(start,zone),local(end,zone)
    if level in MONTHS:
        count=MONTHS[level]
        return shift_month(start,-count).isoformat(),shift_month(end,-count).isoformat()
    delta=end-start
    return (start-delta).isoformat(),start.isoformat()


def buckets(start, end, level, zone=DEFAULT_TIMEZONE, day_start_hour=DEFAULT_DAY_START_HOUR):
    current,upper=local(start,zone),local(end,zone)
    result=[]
    while current<upper:
        day_start=current.replace(hour=day_start_hour,minute=0,second=0,microsecond=0)
        if level in ('day','week'):following=day_start+timedelta(days=1)
        elif level=='month':following=day_start+timedelta(days=7-day_start.weekday())
        else:following=shift_month(day_start.replace(day=1),1)
        following=min(following,upper)
        result.append((current.isoformat(),following.isoformat()))
        current=following
    return result


def days(start,end,zone=DEFAULT_TIMEZONE,day_start_hour=DEFAULT_DAY_START_HOUR):
    return buckets(start,end,'week',zone,day_start_hour)


def logical_date(value,zone,day_start_hour=DEFAULT_DAY_START_HOUR):
    """Date label for a reporting day that begins at day_start_hour."""
    value=local(value,zone)
    return (value-timedelta(days=1) if value.hour<day_start_hour else value).date().isoformat()


def hourly(start,end,zone):
    """Real one-hour spans, including distinct repeated DST hours."""
    current=local(start,zone).astimezone(timezone.utc)
    upper=local(end,zone).astimezone(timezone.utc)
    result=[]
    while current<upper:
        following=min(current+timedelta(hours=1),upper)
        result.append((current.astimezone(ZoneInfo(zone)).isoformat(),following.astimezone(ZoneInfo(zone)).isoformat()))
        current=following
    return result


def seconds(start,end):
    return (end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds()
