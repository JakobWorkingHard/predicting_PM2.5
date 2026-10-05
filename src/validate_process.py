def check_data_quality(df):
    """
    Kontrollera datakvaliteten innan rensning.
    """

    print("Shape:")
    print(df.shape)

    print("\nDatatypes:")
    print(df.dtypes)

    print("\nMissing values:")
    print(df.isna().sum())

    print("\nMissing percentage:")
    print(df.isna().mean() * 100)

    print("\nNumeric summary:")
    print(df.describe())

    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    print("\nDuplicate timestamps:")
    print(df["timestamp"].duplicated().sum())

    print("\nTime range:")
    print(df["timestamp"].min())
    print(df["timestamp"].max())

    print("\nTime gaps:")
    print(
        df["timestamp"]
        .sort_values()
        .diff()
        .value_counts()
        .head()
    )