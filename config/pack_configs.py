from .cell_configs import JP50, _30PL

SR_17 = {
    "n_series": 140,
    "n_parallel": 3,
    "cell_model": JP50,
    
    "enclosure_heat_capacity_J/K": 4770,
    "enclosure_bottom_area_m2": 0.12,
    "enclosure_length_m": 0.285,
    "module_to_enclosure_thermal_conductance_W/K": 1,
}

SR_18_5p = {
    "n_series": 140,
    "n_parallel": 5,
    "cell_model": _30PL,
    "enclosure_heat_capacity_J/K": 4770,
    "enclosure_bottom_area_m2": 0.12,
    "enclosure_length_m": 0.285,
    "module_to_enclosure_thermal_conductance_W/K": 1,
}

SR_18_6p = {
    "n_series": 140,
    "n_parallel": 6,
    "cell_model": _30PL,
    "enclosure_heat_capacity_J/K": 4770,
    "enclosure_bottom_area_m2": 0.174,
    "enclosure_length_m": 0.365,
    "module_to_enclosure_thermal_conductance_W/K": 1,
}
