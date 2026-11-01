import csv
import pandas as pd


def get_profiles(csv_path, channel_names):
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)

        # Skip metadata until the Time header is found.
        for row in reader:
            if row and row[0] == "Time":
                headers = row
                break
        else:
            raise ValueError("Couldn't find Time header")

        # Read the next nonblank row: channel units.
        units = next(
            (row for row in reader if any(value.strip() for value in row)),
            None,
        )
        if units is None:
            raise ValueError("Missing units")

        # Read data, ignoring blank lines.
        rows = [row for row in reader if any(value.strip() for value in row)]

    data = pd.DataFrame(rows, columns=headers)

    # Convert both collections to sets before subtraction.
    missing = set(channel_names.values()) - set(data.columns)
    if missing:
        raise ValueError(f"Missing CSV channels: {sorted(missing)}")

    # Select channels and rename to internal names.
    data = data[list(channel_names.values())].copy()
    data.columns = list(channel_names.keys())

    # Convert strings to numbers.
    data = data.apply(pd.to_numeric, errors="raise")

    if data.empty or data.isna().any().any():
        raise ValueError("Telemetry is empty or contains missing values.")

    if not data["time_s"].diff().iloc[1:].gt(0).all():
        raise ValueError("Time must increase strictly.")

    # Retain exported units.
    original_units = dict(zip(headers, units))
    data.attrs["units"] = {
        name: original_units[csv_name] for name, csv_name in channel_names.items()
    }

    return data
