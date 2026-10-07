import pandas as pd
import pytest

from src.validate_process import (
    convert_datetime,
    sort_by_time,
    check_duplicates,
    ensure_complete_timeline,
    find_nan_gaps
)


def test_convert_datetime():
    df = pd.DataFrame({
        "tid": [
            "2025-01-01 12:00:00+01:00",
            "2025-07-01 12:00:00+02:00"
        ]
    })

    result = convert_datetime(df)

    assert str(result["tid"].dt.tz) == "Europe/Stockholm"


def test_sort_by_time():
    df = pd.DataFrame({
        "tid": [
            "2025-01-01 14:00:00+01:00",
            "2025-01-01 12:00:00+01:00",
            "2025-01-01 13:00:00+01:00"
        ]
    })

    df = convert_datetime(df)
    result = sort_by_time(df)

    assert result["tid"].is_monotonic_increasing


def test_check_duplicates():
    df = pd.DataFrame({
        "tid": [
            "2025-01-01 12:00:00+01:00",
            "2025-01-01 13:00:00+01:00",
            "2025-01-01 13:00:00+01:00"
        ]
    })

    df = convert_datetime(df)

    with pytest.raises(ValueError):
        check_duplicates(df)

def test_ensure_complete_timeline():
    df = pd.DataFrame({
        "tid": [
            "2025-01-01 12:00:00+01:00",
            "2025-01-01 13:00:00+01:00",
            "2025-01-01 15:00:00+01:00"
        ],
        "pm25": [8.1, 8.4, 7.9]
    })

    df = convert_datetime(df)
    result = ensure_complete_timeline(df)

    assert len(result) == 4
    assert result["pm25"].isna().sum() == 1


def test_find_nan_gaps():
    df = pd.DataFrame({
        "tid": pd.date_range(
            "2025-01-01 12:00",
            periods=7,
            freq="h",
            tz="Europe/Stockholm"
        ),
        "pm25": [8.1, None, None, None, 7.9, None, 8.2]
    })

    result = find_nan_gaps(df, "pm25")

    assert len(result) == 2
    assert result["hours"].tolist() == [3, 1]