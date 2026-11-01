from battery_pack import BatteryPack
import numpy as np
import pandas as pd

def simulate(battery_pack: BatteryPack, data, max_step_s=1.0):
  time = data["time_s"].to_numpy(dtype=float)
  power = data["pack_power_W"].to_numpy(dtype=float)
  speed = data["speed_mps"].to_numpy(dtype=float)

  records = []

  def evaluate(i):
    """Calculate electrical quantities and heat rates at current state."""
    battery_pack.set_speed(speed[i])
    battery_pack.get_pack_ocv()
    battery_pack.get_pack_resistance()
    battery_pack.get_pack_current(power[i])
    battery_pack.get_pack_voltage()
    battery_pack.update_heat()

  for i in range(len(time)):
      evaluate(i)

      cell_temp, enclosure_temp = battery_pack.get_temperatures()

      # All values in this row correspond to time[i].
      records.append({
          "soc": battery_pack.soc,
          "predicted_cell_temp_c": cell_temp,
          "predicted_enclosure_temp_c": enclosure_temp,
          "predicted_pack_current_a": battery_pack.pack_current,
          "predicted_pack_voltage_v": battery_pack.pack_voltage,
          "pack_ocv_v": battery_pack.pack_ocv,
          "pack_resistance_ohm": battery_pack.pack_resistance,
          "cell_heat_w": battery_pack.cell_heat_gen_W,
          "cells_to_enclosure_heat_w":
              battery_pack.cell_enclosure_transfer_W,
          "enclosure_to_ambient_heat_w":
              battery_pack.pack_convection_W,
      })

      # The final sample has no following interval to integrate.
      if i == len(time) - 1:
          break

      interval_s = time[i + 1] - time[i]
      steps = int(np.ceil(interval_s / max_step_s))
      dt = interval_s / steps

      for _ in range(steps):
          # Hold the profile inputs constant over this interval.
          # Recalculate resistance/current as SOC and temperature change.
          evaluate(i)

          battery_pack.set_pack_charge(dt)
          battery_pack.update_temps(dt)

  predictions = pd.DataFrame(records, index=data.index)

  results = data.copy()
  results[predictions.columns] = predictions

  return results



