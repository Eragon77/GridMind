import pandas as pd
import requests
import statistics

class Battery:
    def __init__(self, capacity_max, min_soc=0.10):
        self.capacity_max = capacity_max
        self.min_capacity = capacity_max * min_soc
        self.level = capacity_max

    def drain(self, energy_needed):
        available = self.level - self.min_capacity
        if energy_needed <= available:
            self.level -= energy_needed
            return energy_needed
        else:
            drained = available
            self.level = self.min_capacity
            return drained

    def charge(self, energy_added):
        space = self.capacity_max - self.level
        actual_added = min(energy_added, space)
        self.level += actual_added
        return actual_added

def fetch_market_prices(bzn="FR"):
    url = f"https://api.energy-charts.info/price?bzn={bzn}"
    response = requests.get(url)
    data = response.json()
    prices_mwh = data.get("price", [])
    return [p / 1000.0 for p in prices_mwh]

raw_prices = fetch_market_prices("FR")
consumption_data = pd.read_csv("data/household_power_consumption.txt", sep=";", na_values="?", nrows=1000)

min_p = min(raw_prices)
max_p = max(raw_prices)
normalized_prices = [(p - min_p) / (max_p - min_p) for p in raw_prices]

daily_median_norm = statistics.median(normalized_prices) if normalized_prices else 0.5

my_battery = Battery(capacity_max=13.5, min_soc=0.10)
total_cost_with_battery = 0.0
total_cost_without_battery = 0.0

print(f"--- SIMULATION START (Normalized Median: {daily_median_norm:.4f}) ---\n")

for row in consumption_data.itertuples(index=False):
    consumed_kw = float(str(row.Global_active_power))
    consumed_kwh = consumed_kw / 60

    time_parts = str(row.Time).split(":")
    hour = int(time_parts[0])
    minute = int(time_parts[1])

    slot_index = (hour * 60 + minute) // 15

    curr_norm = normalized_prices[slot_index % len(normalized_prices)]
    curr_real = raw_prices[slot_index % len(raw_prices)]

    cost_no_bat = consumed_kwh * curr_real
    total_cost_without_battery += cost_no_bat

    if curr_norm < daily_median_norm * 0.90:
        charged = my_battery.charge(0.05)
        action = "CHARGE"
        cost_bat = (charged * curr_real) + cost_no_bat
    else:
        drained = my_battery.drain(consumed_kwh)
        unmet_load = consumed_kwh - drained
        action = "DISCHARGE"
        cost_bat = unmet_load * curr_real

    total_cost_with_battery += cost_bat
    print(f"[{row.Time}] Norm Price: {curr_norm:.4f} | Action: {action} | Battery: {my_battery.level:.4f} kWh")

savings = total_cost_without_battery - total_cost_with_battery
print(f"\n--- SIMULATION END ---")
print(f"Cost WITHOUT Battery: {total_cost_without_battery:.4f} EUR")
print(f"Cost WITH Battery:    {total_cost_with_battery:.4f} EUR")
print(f"Total Savings:        {savings:.4f} EUR")