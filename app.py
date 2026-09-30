import os
import sys

# Make the repo root importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Streamlit Cloud ships an old sqlite3 that CrewAI's dependencies reject.
# Swap in pysqlite3 when it is available (see requirements.txt).
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st

from solar_crew import run_solar_analysis

st.set_page_config(page_title="SolarAI", page_icon="☀️", layout="wide")

st.title("☀️ SolarAI")
st.caption("Multi-Agent Solar Engineering Consultant")

st.info(
    "Enter a customer's basic electrical information. SolarAI uses a CrewAI team "
    "of specialized engineering agents and a Chief Solar Engineer to produce a proposal."
)

with st.sidebar:
    st.header("Customer Information")
    location = st.text_input("Location", "Peshawar")
    monthly_bill = st.number_input(
        "Monthly electricity bill (PKR)", min_value=0.0, value=45000.0, step=1000.0
    )
    peak_sun_hours = st.number_input(
        "Peak sun hours/day", min_value=1.0, max_value=8.0, value=5.0, step=0.5
    )
    panel_watt = st.number_input(
        "Panel rating (W)", min_value=100, max_value=1000, value=585, step=5
    )
    inverter_kw = st.number_input(
        "Preferred inverter size (kW)", min_value=1.0, max_value=100.0, value=10.0, step=0.5
    )

    st.subheader("Loads")
    ac_qty = st.number_input("2-ton AC quantity", 0, 10, 1)
    ac_hours = st.number_input("AC hours/day", 0.0, 24.0, 6.0, 0.5)
    fridge_qty = st.number_input("Refrigerator quantity", 0, 10, 1)
    fridge_hours = st.number_input("Refrigerator hours/day", 0.0, 24.0, 12.0, 0.5)
    dispenser_qty = st.number_input("Water dispenser quantity", 0, 10, 1)
    dispenser_hours = st.number_input("Dispenser hours/day", 0.0, 24.0, 4.0, 0.5)
    fan_qty = st.number_input("Fan quantity", 0, 30, 5)
    fan_hours = st.number_input("Fan hours/day", 0.0, 24.0, 8.0, 0.5)
    light_qty = st.number_input("Light quantity", 0, 50, 10)
    light_hours = st.number_input("Light hours/day", 0.0, 24.0, 6.0, 0.5)
    tv_qty = st.number_input("TV quantity", 0, 10, 1)
    tv_hours = st.number_input("TV hours/day", 0.0, 24.0, 5.0, 0.5)

    st.subheader("AI model")
    model = st.selectbox(
        "Groq model",
        [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ],
        index=0,
        help="llama-3.1-8b-instant is fastest, llama-3.3-70b-versatile is a good balance, gpt-oss models reason longer and are slower.",
    )

    run = st.button("🚀 Run SolarAI", type="primary", use_container_width=True)

if run:
    if "GROQ_API_KEY" not in st.secrets:
        st.error("GROQ_API_KEY is missing. Add it in Streamlit Cloud → App settings → Secrets.")
        st.stop()

    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

    customer_data = {
        "location": location,
        "monthly_bill_pkr": monthly_bill,
        "peak_sun_hours": peak_sun_hours,
        "panel_watt": panel_watt,
        "preferred_inverter_kw": inverter_kw,
        "loads": {
            "2_ton_ac": {"quantity": ac_qty, "hours_per_day": ac_hours},
            "refrigerator": {"quantity": fridge_qty, "hours_per_day": fridge_hours},
            "water_dispenser": {"quantity": dispenser_qty, "hours_per_day": dispenser_hours},
            "fans": {"quantity": fan_qty, "hours_per_day": fan_hours},
            "lights": {"quantity": light_qty, "hours_per_day": light_hours},
            "tv": {"quantity": tv_qty, "hours_per_day": tv_hours},
        },
    }

    st.session_state["last_customer_data"] = customer_data

    with st.status("🤖 SolarAI agents are collaborating...", expanded=True) as status:
        st.write("⚡ Load Engineer — analyzing demand...")
        st.write("☀️ Solar Design Engineer — sizing PV system...")
        st.write("🔋 Battery Engineer — comparing storage options...")
        st.write("💰 Financial Analyst — estimating economics...")
        st.write("🛡️ Safety Engineer — reviewing protection...")
        st.write("👨‍💼 Chief Solar Engineer — preparing final proposal...")

        try:
            result = run_solar_analysis(customer_data, model=model)
            st.session_state["result"] = result
            status.update(label="✅ SolarAI analysis completed", state="complete")
        except Exception as exc:
            status.update(label="❌ Analysis failed", state="error")
            st.exception(exc)
            st.stop()

if "result" in st.session_state:
    st.divider()
    st.subheader("📊 SolarAI Professional Proposal")
    st.markdown(st.session_state["result"])

    st.download_button(
        "⬇️ Download proposal as Markdown",
        data=st.session_state["result"],
        file_name="solarai_proposal.md",
        mime="text/markdown",
    )
else:
    st.subheader("🤖 Agent War Room")
    cols = st.columns(6)
    agents = [
        ("⚡", "Load Engineer"),
        ("☀️", "Solar Designer"),
        ("🔋", "Battery Engineer"),
        ("💰", "Financial Analyst"),
        ("🛡️", "Safety Engineer"),
        ("👨‍💼", "Chief Engineer"),
    ]
    for col, (icon, name) in zip(cols, agents):
        with col:
            st.metric(name, "Waiting", delta=icon)
