def get_heat_gen(resistance, current):
    heat_gen = resistance * current ** 2
    return heat_gen

def get_cell_to_enclosure_heat_transfer(cell_temp, enclosure_temp, thermal_conductance):
    heat_transfer = thermal_conductance * (cell_temp - enclosure_temp)
    return heat_transfer

def get_convection_heat_transfer(ambient_C, enclosure_temp, pack_length, pack_area, speed):
    # Approximate air properties at 300 K (~27°C), 1 atm.
    kinematic_viscosity = 1.589e-5  # m²/s
    air_conductivity = 0.0263  # W/(m·K)
    prandtl_number = 0.707  # dimensionless

    reynolds_number = speed * pack_length / kinematic_viscosity

    if reynolds_number < 500_000:
        #laminar
        nusselt_number = 0.664 * reynolds_number**0.5 * prandtl_number ** (1 / 3)
    else:
        #turbulent
        nusselt_number = (0.037 * reynolds_number**0.8 - 871) * prandtl_number ** (
            1 / 3
        )

    h = nusselt_number * air_conductivity / pack_length

    heat_transfer = h * pack_area * (enclosure_temp - ambient_C)
    return heat_transfer
    