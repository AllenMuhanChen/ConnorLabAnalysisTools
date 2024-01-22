import time
import datetime




class When:
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def tuple(self):
        return (self.start, self.stop)

    def __str__(self):
        return "({},{})".format(self.start, self.stop)

    def __repr__(self):
        return self.__str__()


def today() -> When:
    today = to_unix(datetime.date.today())
    tomorrow = to_unix(datetime.date.today() + datetime.timedelta(days=1))
    when = When(today, tomorrow)
    return when


def from_x_days_ago(x):
    start = to_unix(datetime.date.today() - datetime.timedelta(days=x))
    stop = now()
    when = When(start, stop)
    return when


def from_date_to_now(year: int, month: int, day: int) -> When:
    start = to_unix(datetime.date(year, month, day))
    stop = now()
    when = When(start, stop)
    return when

def all():
    when = When(0, to_unix(datetime.date.fromisoformat('3022-01-01')))
    return when


def now():
    return round(time.time() * 1000000)


def to_unix(dt: datetime.datetime):
    return round(time.mktime(dt.timetuple()) * 1000000)


def on_date(year: int, month: int, day: int) -> When:
    """
    Returns a When object representing the start and end of the 24-hour period for the given date.

    :param year: Year component of the date.
    :param month: Month component of the date.
    :param day: Day component of the date.
    :return: When object representing the start and end of the given date.
    """
    date = datetime.date(year, month, day)
    start = to_unix(date)
    end = to_unix(date + datetime.timedelta(days=1))
    return When(start, end)


def on_date_and_time(year: int, month: int, day: int, start_time: str = None, end_time: str = None) -> When:
    """
    Returns a When object representing the period from the given start date and optional start time to an optional end time or the end of the day if no end time is provided.

    :param year: Year component of the date.
    :param month: Month component of the date.
    :param day: Day component of the date.
    :param start_time: Optional start time as a string in 'HH:MM:SS' format. Defaults to the beginning of the day if not provided.
    :param end_time: Optional end time as a string in 'HH:MM:SS' format. Defaults to the end of the day if not provided.
    :return: When object representing the start and potential end of the given date and time.
    """
    # Determine the start time
    if start_time:
        # Create the start datetime from the date and time components
        start_datetime = datetime.datetime(year, month, day) + datetime.timedelta(seconds=int(start_time[:2])*3600 + int(start_time[3:5])*60 + int(start_time[6:]))
    else:
        # Default to the beginning of the day (00:00:00)
        start_datetime = datetime.datetime(year, month, day)
    start = to_unix(start_datetime)

    # Determine the end time
    if end_time:
        # Create the end datetime from the date and time components
        end_datetime = datetime.datetime(year, month, day) + datetime.timedelta(seconds=int(end_time[:2])*3600 + int(end_time[3:5])*60 + int(end_time[6:]))
    else:
        # Default to the end of the day (23:59:59)
        end_datetime = datetime.datetime(year, month, day, 23, 59, 59)
    end = to_unix(end_datetime)

    return When(start, end)



# Testing the new function with a start time and default end time
test_start_time = "08:30:00"  # 8:30 AM
when_for_date_time = on_date_and_time(2022, 7, 4, test_start_time)
when_for_date_time
