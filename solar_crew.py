"""CrewAI multi-agent orchestration for SolarAI."""

import os

from crewai import Agent, Crew, Process, Task, LLM

from solar_tools import (
    calculate_load,
    calculate_pv_size,
    calculate_battery_options,
)


def _strip_cache_breakpoint(obj):
    """Recursively remove the 'cache_breakpoint' key that newer CrewAI versions add
    to messages but that Groq's API rejects."""
    if isinstance(obj, dict):
        return {k: _strip_cache_breakpoint(v) for k, v in obj.items() if k != "cache_breakpoint"}
    if isinstance(obj, list):
        return [_strip_cache_breakpoint(v) for v in obj]
    return obj


def _patch_litellm():
    """Wrap litellm.completion / acompletion so requests to Groq are accepted."""
    try:
        import litellm
    except ImportError:
        return

    if not getattr(litellm.completion, "_solarai_patched", False):
        _orig_completion = litellm.completion

        def completion(*args, **kwargs):
            if kwargs.get("messages") is not None:
                kwargs["messages"] = _strip_cache_breakpoint(kwargs["messages"])
            return _orig_completion(*args, **kwargs)

        completion._solarai_patched = True
        litellm.completion = completion

    if hasattr(litellm, "acompletion") and not getattr(litellm.acompletion, "_solarai_patched", False):
        _orig_acompletion = litellm.acompletion

        async def acompletion(*args, **kwargs):
            if kwargs.get("messages") is not None:
                kwargs["messages"] = _strip_cache_breakpoint(kwargs["messages"])
            return await _orig_acompletion(*args, **kwargs)

        acompletion._solarai_patched = True
        litellm.acompletion = acompletion


DEFAULT_MODEL = "openai/gpt-oss-120b"


def _llm(model=DEFAULT_MODEL, reasoning_effort=None):
    model = (model or DEFAULT_MODEL).strip()
    if model.startswith("groq/"):
        model = model[len("groq/"):]

    kwargs = {}
    if reasoning_effort in ("low", "medium", "high"):
        kwargs["reasoning_effort"] = reasoning_effort

    return LLM(
        model=f"groq/{model}",
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.1,
        **kwargs,
    )


def build_agents(model=DEFAULT_MODEL, reasoning_effort=None):
    llm = _llm(model, reasoning_effort)

    load_engineer = Agent(
        role="Electrical Load Engineer",
        goal="Analyze customer appliances and produce a transparent load and energy assessment.",
        backstory="You are an electrical engineer specializing in residential load assessment.",
        llm=llm, verbose=False, allow_delegation=False,
    )

    solar_engineer = Agent(
        role="Solar Design Engineer",
        goal="Develop a technically coherent PV and inverter sizing recommendation using the load analysis.",
        backstory="You are a solar PV design engineer who checks system sizing and basic string logic.",
        llm=llm, verbose=False, allow_delegation=False,
    )

    battery_engineer = Agent(
        role="Battery Engineer",
        goal="Compare no-battery, lead-acid and lithium storage options and explain use cases.",
        backstory="You specialize in residential energy storage and backup design.",
        llm=llm, verbose=False, allow_delegation=False,
    )

    financial_analyst = Agent(
        role="Solar Financial Analyst",
        goal="Estimate system economics and clearly state assumptions instead of inventing exact market prices.",
        backstory="You analyze solar project costs, savings and simple payback.",
        llm=llm, verbose=False, allow_delegation=False,
    )

    safety_engineer = Agent(
        role="Electrical Safety Engineer",
        goal="Review the proposal for AC/DC protection, earthing, SPD and cable-sizing considerations.",
        backstory="You focus on electrical protection and safe solar installation practices.",
        llm=llm, verbose=False, allow_delegation=False,
    )

    chief = Agent(
        role="Chief Solar Engineer",
        goal="Synthesize all specialist reports into one professional, transparent solar proposal.",
        backstory="You lead multidisciplinary solar engineering reviews and never hide assumptions or uncertainty.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    return load_engineer, solar_engineer, battery_engineer, financial_analyst, safety_engineer, chief


def run_solar_analysis(data, model=DEFAULT_MODEL, reasoning_effort=None):
    _patch_litellm()

    load_engineer, solar_engineer, battery_engineer, financial_analyst, safety_engineer, chief = build_agents(model, reasoning_effort)

    # Deterministic pre-calculations, handed to the agents as reference figures
    load_calc = calculate_load(data["loads"])
    pv_calc = calculate_pv_size(
        load_calc["estimated_daily_kwh"],
        peak_sun_hours=data["peak_sun_hours"],
        panel_watt=data["panel_watt"],
    )
    battery_calc = calculate_battery_options()

    load_task = Task(
        description=f"""Analyze this residential customer:
{data}

Deterministic load calculation (assumed appliance wattages, use as reference and show assumptions):
{load_calc}

Report connected load, estimated daily kWh, peak demand, AC contribution, and important uncertainties.""",
        expected_output="A concise electrical load assessment with calculations and assumptions. Keep it under about 300 words.",
        agent=load_engineer,
    )

    solar_task = Task(
        description=f"""Using the customer information below and the load assessment, size a conceptual PV system.
Customer: {data}

Deterministic PV sizing reference (80% system factor):
{pv_calc}

Use {data['panel_watt']} W panels, {data['peak_sun_hours']} peak sun hours/day, and a preferred inverter size of {data['preferred_inverter_kw']} kW as inputs.
Discuss PV capacity, panel count, basic string considerations, inverter sizing and DC/AC ratio.
Do not claim a final string design without checking actual panel and inverter datasheets.""",
        expected_output="A conceptual PV and inverter design with explicit assumptions. Keep it under about 300 words.",
        agent=solar_engineer,
        context=[load_task],
    )

    battery_task = Task(
        description=f"""Compare three storage strategies for this customer:
{data}

Reference summary of options:
{battery_calc}

Explain no battery, lead-acid and lithium options. Discuss usable energy, backup purpose, depth of discharge and practical trade-offs.
Do not invent exact prices.""",
        expected_output="A structured battery comparison and recommendation conditions. Keep it under about 300 words.",
        agent=battery_engineer,
        context=[load_task],
    )

    financial_task = Task(
        description=f"""Estimate solar economics for:
{data}
Do not invent a precise local tariff or equipment price. If values are unavailable, provide formulas, ranges or clearly labeled assumptions.
Cover estimated monthly savings, simple payback logic and ROI considerations.""",
        expected_output="A transparent financial analysis with assumptions and formulas. Keep it under about 300 words.",
        agent=financial_analyst,
        context=[load_task, solar_task],
    )

    safety_task = Task(
        description="""Review the proposed solar system from an electrical safety perspective.
Cover DC isolator/fusing, AC protection, surge protection, earthing/bonding, cable sizing, inverter protection and installation checks.
Flag items that require verification against local codes and manufacturer datasheets.""",
        expected_output="A practical safety and protection checklist with verification flags. Keep it under about 300 words.",
        agent=safety_engineer,
        context=[solar_task, battery_task],
    )

    final_task = Task(
        description=f"""Act as the Chief Solar Engineer.

Customer:
{data}

Combine the specialist reports into a professional SolarAI proposal.

Required sections:
1. Executive summary
2. Customer/load profile
3. Load analysis
4. Recommended PV system
5. Panel quantity and conceptual strings
6. Inverter recommendation
7. Battery comparison
8. Financial analysis
9. Protection and safety checklist
10. Assumptions and limitations
11. Recommended next steps

Important:
- Clearly label estimates.
- Never fabricate a product datasheet, tariff, price or regulation.
- Explain that final electrical design must be verified using actual equipment datasheets and applicable local requirements.
- Make the proposal useful to a homeowner while retaining engineering detail.""",
        expected_output="A polished professional solar engineering proposal in Markdown.",
        agent=chief,
        context=[load_task, solar_task, battery_task, financial_task, safety_task],
    )

    crew = Crew(
        agents=[load_engineer, solar_engineer, battery_engineer, financial_analyst, safety_engineer, chief],
        tasks=[load_task, solar_task, battery_task, financial_task, safety_task, final_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)
