import pandas as pd
from src import extracting_data


def test_hamta_pm25_removes_duplicates(monkeypatch, tmp_path):
    # Två identiska observationer vid ett månadsskifte
    timestamp = int(
        pd.Timestamp("2025-07-01 00:00", tz="Europe/Stockholm").timestamp() * 1000
    )

    fake_response = {
        "values": [
            {"timestamp": timestamp, "value": 10.5},
            {"timestamp": timestamp, "value": 10.5},
        ]
    }

    # Ersätt API-anropet med vårt testsvar
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_response

    monkeypatch.setattr(
        extracting_data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse()
    )

    # Hoppa över väntetiden mellan API-anrop
    monkeypatch.setattr(extracting_data.time, "sleep", lambda _: None)

    # Använd en tillfällig sökväg så att ingen befintlig CSV läses
    test_path = tmp_path / "pm25_test.csv"

    df = extracting_data.hamta_pm25(
        "2025-06-30",
        "2025-07-02",
        6247,
        "https://example.com/api",
        test_path
    )

    assert len(df) == 1
    assert df.index.duplicated().sum() == 0
    assert df["pm25"].iloc[0] == 10.5


def test_hamta_pm25_respects_date_range(monkeypatch, tmp_path):
    # En observation inom intervallet och en efter slutdatumet
    timestamps = [
        "2025-12-31 23:00",
        "2026-01-01 00:00",
    ]

    fake_response = {
        "values": [
            {
                "timestamp": int(
                    pd.Timestamp(t, tz="Europe/Stockholm").timestamp() * 1000
                ),
                "value": 10.5,
            }
            for t in timestamps
        ]
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_response

    # Ersätt API-anrop och väntetid
    monkeypatch.setattr(
        extracting_data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse()
    )
    monkeypatch.setattr(extracting_data.time, "sleep", lambda _: None)

    df = extracting_data.hamta_pm25(
        "2025-12-30",
        "2025-12-31",
        6247,
        "https://example.com/api",
        tmp_path / "pm25_test.csv",
    )

    # Endast observationen inom intervallet ska finnas kvar
    assert len(df) == 1
    assert df.index.max() == pd.Timestamp(
        "2025-12-31 23:00", tz="Europe/Stockholm"
    )