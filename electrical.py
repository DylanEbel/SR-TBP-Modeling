import numpy as np


def get_ocv(soc, cell_config):
    """Return cell OCV in volts. SOC is a fraction from 0 to 1."""
    return float(
        np.interp(
            soc,
            cell_config["ocv_soc_fraction"],
            cell_config["ocv_voltage_V"],
        )
    )


def get_resistance(soc, temp_C, cell_config):
    """Return cell resistance in ohms."""
    soc_points = cell_config["resistance_soc_fraction"]
    temp_points = cell_config["resistance_temperature_C"]
    resistance_table = cell_config["resistance_ohm"]

    # Interpolate across SOC within each temperature row.
    resistance_at_each_temp = [
        np.interp(soc, soc_points, row) for row in resistance_table
    ]

    # Interpolate between temperatures.
    return float(
        np.interp(
            temp_C,
            temp_points,
            resistance_at_each_temp,
        )
    )


def get_current(power, ocv, resistance):
    discriminant = ocv**2 - 4 * resistance * power

    if discriminant < 0:
        raise ValueError("Requested power exceeds the model's power limit.")

    return 2 * power / (ocv + np.sqrt(discriminant))
