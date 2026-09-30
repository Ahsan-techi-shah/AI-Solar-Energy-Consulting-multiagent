"""Deterministic solar engineering calculations used by SolarAI."""

DEFAULT_APPLIANCE_WATTS = {
    "2_ton_ac": 1800,
    "refrigerator": 180,
    "water_dispenser": 500,
    "fans": 75,
    "lights": 12,
    "tv": 100,
}


def appliance_power_watts(name):
    return DEFAULT_APPLIANCE_WATTS.get(name, 100)


def calculate_load(loads):
    total_connected_w = 0
    daily_kwh = 0
    details = {}

    for name, values in loads.items():
        qty = float(values.get("quantity", 0))
        hours = float(values.get("hours_per_day", 0))
        watts = appliance_power_watts(name)
        connected = qty * watts
        energy = connected * hours / 1000

        total_connected_w += connected
        daily_kwh += energy
        details[name] = {
            "assumed_watts_each": watts,
            "quantity": qty,
            "hours_per_day": hours,
            "connected_w": connected,
            "daily_kwh": energy,
        }

    return {
        "connected_load_kw": total_connected_w / 1000,
        "estimated_daily_kwh": daily_kwh,
        "details": details,
    }


def calculate_pv_size(daily_kwh, peak_sun_hours=5.0, system_factor=0.80, panel_watt=585):
    if peak_sun_hours <= 0 or system_factor <= 0:
        raise ValueError("Peak sun hours and system factor must be positive.")

    pv_kw = daily_kwh / (peak_sun_hours * system_factor)
    panels = max(1, int((pv_kw * 1000 + panel_watt - 1) // panel_watt))
    actual_kw = panels * panel_watt / 1000
    return {
        "required_pv_kw": pv_kw,
        "panel_count": panels,
        "actual_pv_kw": actual_kw,
    }


def calculate_battery_options():
    return {
        "no_battery": "Grid-tied operation; no backup energy storage.",
        "lead_acid": "Lower upfront cost in many markets but lower usable energy and shorter cycle life.",
        "lithium": "Higher upfront cost in many markets but generally higher usable energy and cycle life.",
    }


def calculate_financials(system_cost, monthly_savings):
    if monthly_savings <= 0:
        return {"payback_years": None, "roi_percent_year": None}
    payback_years = system_cost / (monthly_savings * 12)
    roi = (monthly_savings * 12 / system_cost) * 100
    return {"payback_years": payback_years, "roi_percent_year": roi}
