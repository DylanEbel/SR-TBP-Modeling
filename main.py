from config.pack_configs import SR_17
from config.pack_configs import SR_18_5p
from config.pack_configs import SR_18_6p
from config.sim_configs import SIM1
from model import simulate
from profiles import get_profiles
from battery_pack import BatteryPack
from plot_results import plot_results, summarize_results

csv_data_name = "2026-6-7-Regen-Run-3"
csv_data_path = f"data/{csv_data_name}.csv"
channel_names = {
    "time_s": "Time",
    "pack_current_a": "VCU Shunt Current A",
    "pack_voltage_v": "BMS Total Pack Voltage",
    "cell_temp_max_c": "BMS Highest Cell Temperature",
    "cell_temp_avg_c": "BMS Average Cell Temperature",
    "speed_mps": "GPS Speed",
    "pack_power_W": "SHUNT Power W",
}


def main():
    data = get_profiles(csv_data_path, channel_names)

    configs = {
        "SR-17": SR_17,
        "SR-18 5p": SR_18_5p,
        "SR-18 6p": SR_18_6p,
    }

    results = {
        name: simulate(BatteryPack(config, SIM1), data)
        for name, config in configs.items()
    }

    print(summarize_results(results).round(2))

    fig, axes = plot_results(
        results,
        measured_from="SR-17",
        save_path="plots/pack_comparison.png",
    )


if __name__ == "__main__":
    main()
