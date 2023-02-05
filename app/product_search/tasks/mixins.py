import datetime
from dateutil.rrule import rrule, MONTHLY


class ParseSkuMixin:
    """Класс миксин с утилитами"""

    def match(self, text, alphabet=set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')):
        return not alphabet.isdisjoint(text.lower())

    def get_date(self, delta: int):
        d2 = datetime.datetime.now() - datetime.timedelta(days=1)
        d2 = d2.date()
        d1 = d2 - datetime.timedelta(days=delta)
        return d1, d2

    def get_period_date(self, first_date):
        dates = []
        first_date = datetime.datetime.strptime(first_date, '%Y-%m-%d').date()

        now = datetime.datetime.now().date()
        now = now - datetime.timedelta(days=now.day - 1)

        start_date = datetime.datetime.now().date() - datetime.timedelta(weeks=52)
        if first_date < start_date:
            day_delta = start_date.day
            start_date = start_date - datetime.timedelta(days=day_delta - 1)
        else:
            day_delta = first_date.day
            start_date = first_date - datetime.timedelta(days=day_delta - 1)
        freq_date = list(rrule(freq=MONTHLY, count=13, dtstart=start_date))

        for idx, date in enumerate(freq_date):
            if date == datetime.datetime.strptime(str(now), '%Y-%m-%d'):
                break
            if idx + 1 != len(freq_date):
                dates.append({
                    "d1": freq_date[idx].date(),
                    "d2": freq_date[idx + 1].date()
                })
        return dates
