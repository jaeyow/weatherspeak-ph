import datetime
import pytest
from modal_etl.step4_upload import _infer_issued_at


def _utc(year, month, day, hour=0) -> datetime.datetime:
    return datetime.datetime(year, month, day, hour, 0, 0,
                             tzinfo=datetime.timezone.utc)


def test_infer_issued_at_same_bulletin_number():
    """When hist_num == latest_num, result equals latest."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=5, hist_num=5)
    assert result == latest


def test_infer_issued_at_one_bulletin_back():
    """One bulletin back = 6 hours earlier."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=23, hist_num=22)
    assert result == _utc(2026, 4, 22, 17)


def test_infer_issued_at_many_bulletins_back():
    """Bulletin #1 of 23 = 22 steps × 6 h = 132 h earlier."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=23, hist_num=1)
    expected = latest - datetime.timedelta(hours=132)
    assert result == expected


def test_infer_issued_at_preserves_timezone():
    """Result keeps the timezone of latest_issued_at."""
    tz = datetime.timezone(datetime.timedelta(hours=8))
    latest = datetime.datetime(2026, 4, 22, 23, 0, 0, tzinfo=tz)
    result = _infer_issued_at(latest, latest_num=3, hist_num=1)
    assert result.tzinfo == tz
