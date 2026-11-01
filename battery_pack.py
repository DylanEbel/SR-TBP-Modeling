from electrical import get_ocv, get_resistance , get_current
from thermal import get_heat_gen, get_cell_to_enclosure_heat_transfer, get_convection_heat_transfer
import numpy as np

class BatteryPack:

    def __init__(self, pack_config, sim_config, inital_soc=1.0):
        self.config = pack_config
        self.cell_config = pack_config["cell_model"]

        self.n_series = pack_config["n_series"]
        self.n_parallel = pack_config["n_parallel"]

        self.set_soc(inital_soc)

        self.max_pack_charge = self.n_parallel * self.cell_config["cell_capacity_Ah"] * 3600 * inital_soc
        self.pack_charge = self.max_pack_charge

        self.cell_heat_capacity_J_K = self.n_series * self.n_parallel * self.cell_config["cell_mass_kg"] * self.cell_config["cell_specific_heat_J_kgK"]

        self.ambient = sim_config["ambient_c"]
        self.is_adiabatic = sim_config["adiabatic"]

        self.cell_temperature_C = sim_config["start_temp"]
        self.enclosure_temperature_C = sim_config["start_temp"]

        self.enclosure_thermal_capacity = pack_config["enclosure_heat_capacity_J/K"]
        self.cell_thermal_capacity = self.cell_config["cell_specific_heat_J_kgK"] * self.cell_config["cell_mass_kg"] * self.n_series * self.n_parallel

    # electrical pack updates
    def get_pack_resistance(self):
        cell_resistance = get_resistance(self.soc, self.cell_temperature_C, self.cell_config)
        self.pack_resistance = cell_resistance * self.n_series / self.n_parallel
        return self.pack_resistance

    def get_pack_ocv(self):
        cell_ocv = get_ocv(self.soc, self.cell_config)
        self.pack_ocv = cell_ocv * self.n_series
        return self.pack_ocv

    def get_pack_current(self, power):
        self.pack_current = get_current(power, self.pack_ocv, self.pack_resistance)
        return self.pack_current

    def get_pack_voltage(self):
        self.pack_voltage = self.pack_ocv - self.pack_resistance * self.pack_current
        return self.pack_voltage

    def set_pack_charge(self, time_step):
        self.pack_charge -= self.pack_current * time_step
        new_soc = self.pack_charge / self.max_pack_charge
        self.set_soc(new_soc)

    def set_soc(self, soc):
        self.soc = float(soc)

    def set_speed(self, speed):
        self.speed = speed

    # thermal updates
    def update_heat(self):
        self.cell_heat_gen_W = get_heat_gen(self.pack_resistance, self.pack_current)
        self.cell_enclosure_transfer_W = get_cell_to_enclosure_heat_transfer(self.cell_temperature_C, self.enclosure_temperature_C, self.config["module_to_enclosure_thermal_conductance_W/K"])
        if not self.is_adiabatic:
            self.pack_convection_W = get_convection_heat_transfer(self.ambient, self.enclosure_temperature_C, self.config["enclosure_length_m"], self.config["enclosure_bottom_area_m2"], self.speed)
        else:
            self.pack_convection_W = 0

    def update_temps(self, time_step):
        self.cell_temperature_C += ((self.cell_heat_gen_W - self.cell_enclosure_transfer_W) * time_step / self.cell_thermal_capacity)
        self.enclosure_temperature_C += ((self.cell_enclosure_transfer_W - self.pack_convection_W) * time_step / self.enclosure_thermal_capacity)

    def get_temperatures(self):
        return [self.cell_temperature_C, self.enclosure_temperature_C]
