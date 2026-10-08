import pandas as pd
import pytest

from src.validate_process import (
    convert_datetime,
    sort_by_time,
    check_duplicates,
    ensure_complete_timeline,
    replace_invalid_values,
    find_nan_gaps,
    interpolate_short_gaps,
    interpolate_wind_direction,
    fill_short_rain_gaps,
    preprocess_data,
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


def test_replace_invalid_values():
    df = pd.DataFrame({
        "pm25": [10.0, -1.0],
        "Lufttemperatur": [20.0, 25.0],
        "Vindhastighet": [3.0, -2.0],
        "Relativ luftfuktighet": [50.0, 120.0],
        "Nederbördsmängd": [0.0, -1.0],
        "Vindriktning": [360.0, 361.0],
    })

    result = replace_invalid_values(df)

    # Giltiga värden ska behållas
    assert result.loc[0, "pm25"] == 10.0
    assert result.loc[0, "Vindhastighet"] == 3.0
    assert result.loc[0, "Relativ luftfuktighet"] == 50.0
    assert result.loc[0, "Nederbördsmängd"] == 0.0

    # 360° ska normaliseras till 0°
    assert result.loc[0, "Vindriktning"] == 0.0

    # Ogiltiga värden ska bli NaN
    assert pd.isna(result.loc[1, "pm25"])
    assert pd.isna(result.loc[1, "Vindhastighet"])
    assert pd.isna(result.loc[1, "Relativ luftfuktighet"])
    assert pd.isna(result.loc[1, "Nederbördsmängd"])
    assert pd.isna(result.loc[1, "Vindriktning"])


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


def test_interpolate_short_gaps():
    df = pd.DataFrame({
        "tid": pd.date_range(
            "2026-01-01 00:00",
            periods=10,
            freq="h",
            tz="Europe/Stockholm"
        ),
        "pm25": [
            10.0,
            11.0,
            None,
            None,
            14.0,   # lucka på 2 h → ska fyllas
            None,
            None,
            None,
            None,
            20.0    # lucka på 4 h → ska inte fyllas
        ]
    })

    result = interpolate_short_gaps(df, "pm25")

    # Den korta luckan ska interpoleras
    assert result.loc[2, "pm25"] == 12.0
    assert result.loc[3, "pm25"] == 13.0

    # Den långa luckan ska vara kvar som NaN
    assert result.loc[5:8, "pm25"].isna().all()


def test_interpolate_wind_direction():
    df = pd.DataFrame({
        "tid": pd.date_range(
            "2026-01-01 00:00",
            periods=3,
            freq="h",
            tz="Europe/Stockholm"
        ),
        "Vindriktning": [
            350.0,
            None,
            10.0
        ]
    })

    result = interpolate_wind_direction(df)

    # Mittenvärdet ska interpoleras över 0°,
    # inte linjärt till 180°
    interpolated = float(result.loc[1, "Vindriktning"])

    assert interpolated == pytest.approx(0.0)


def test_fill_short_rain_gaps():
    df = pd.DataFrame({
        "tid": pd.date_range(
            "2026-01-01 00:00",
            periods=14,
            freq="h",
            tz="Europe/Stockholm"
        ),
        "Nederbördsmängd": [
            0.0,
            None,       # kort lucka, 0 före och efter → fylls
            0.0,
            1.0,
            None,       # kort lucka, regn före → ska inte fyllas
            0.0,
            0.0,
            None,       # lång lucka på 4 h → ska inte fyllas
            None,
            None,
            None,
            0.0,
            0.0,
            0.0
        ]
    })

    result = fill_short_rain_gaps(df)

    # Kort lucka med 0 före och efter ska fyllas med 0
    assert result.loc[1, "Nederbördsmängd"] == 0.0

    # Kort lucka med regn före ska vara kvar som NaN
    assert pd.isna(result.loc[4, "Nederbördsmängd"])

    # Lucka på 4 timmar ska vara kvar som NaN
    assert result.loc[7:10, "Nederbördsmängd"].isna().all()


def test_preprocess_data():
    df = pd.DataFrame({
        "tid": pd.date_range(
            "2026-01-01 00:00",
            periods=5,
            freq="h",
            tz="UTC"
        ).astype(str),

        "pm25": [
            10.0,
            -5.0,
            12.0,
            13.0,
            14.0
        ],

        "Lufttemperatur": [
            5.0,
            None,
            7.0,
            8.0,
            9.0
        ],

        "Vindriktning": [
            350.0,
            360.0,
            10.0,
            20.0,
            30.0
        ],

        "Vindhastighet": [
            2.0,
            None,
            4.0,
            5.0,
            6.0
        ],

        "Relativ luftfuktighet": [
            70.0,
            None,
            72.0,
            73.0,
            74.0
        ],

        "Nederbördsmängd": [
            0.0,
            None,
            0.0,
            0.0,
            0.0
        ]
    })

    result = preprocess_data(df)

    # Tid ska vara timezone-aware och konverterad till svensk tid
    assert str(result["tid"].dt.tz) == "Europe/Stockholm"

    # Linjär interpolation
    assert result.loc[1, "pm25"] == 11.0
    assert result.loc[1, "Lufttemperatur"] == 6.0
    assert result.loc[1, "Vindhastighet"] == 3.0
    assert result.loc[1, "Relativ luftfuktighet"] == 71.0

    # Cirkulär interpolation: 350° → 0° → 10°
    assert result.loc[1, "Vindriktning"] == pytest.approx(0.0)

    # Nederbörd: 0 → NaN → 0 ska bli 0
    assert result.loc[1, "Nederbördsmängd"] == 0.0

    # Resultatet ska inte innehålla några NaN i detta testdataset
    assert not result.isna().any().any()