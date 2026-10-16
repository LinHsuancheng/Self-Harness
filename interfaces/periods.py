"""Calendar ranges and bucket boundaries in the configured report timezone."""
import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LEVELS=('day','week','month','quarter','halfyear','year')
MONTHS={'month':1,'quarter':3,'halfyear':6,'year':12}


def local(value, zone):
    value=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if value.tzinfo is None:
        value=value.replace(tzinfo=ZoneInfo(zone))
    return value.astimezone(ZoneInfo(zone))


def shift_month(value, count):
    index=value.year*12+value.month-1+count
    year,month=divmod(index,12);month+=1
    return value.replace(year=year,month=month,day=min(value.day,calendar.monthrange(year,month)[1]))


def bounds(level, anchor, zone, day_start_hour=0):
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


def buckets(start, end, level, zone, day_start_hour=0):
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


def days(start,end,zone,day_start_hour=0):
    return buckets(start,end,'week',zone,day_start_hour)


def seconds(start,end):
    return (end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds()
