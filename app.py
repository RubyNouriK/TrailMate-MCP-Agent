# app.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import StructuredTool

# Tools
from tools.pipeline import recommend_near_place
from tools.trails_api import get_trails_near, get_trails_in_bbox
from tools.weather_data import get_weather, weather_for_trail
from tools.geocode import geocode_place

# --- Config
ENV_PATH = Path(__file__).resolve().parent / "config" / "openai_key.env"
load_dotenv(dotenv_path=ENV_PATH)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "parse_pref.txt"
try:
    SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()
except FileNotFoundError:
    SYSTEM_PROMPT = (
        "You are TrailMate, a route recommender for Alberta, Canada. "
        "Use tools to find trails and check weather before recommending."
    )

DEBUG = False  # NEW: flip to True to see intermediate tool calls in the UI

# --- Tools
recommend_near_place_tool = StructuredTool.from_function(
    func=recommend_near_place,
    name="recommend_near_place",
    description=(
        "One-shot pipeline for an Alberta place name. "
        "Inputs: place (str), radius_km (float, default 12), hours (int, default 12), hard (bool, default False). "
        "It geocodes the place, finds nearby trails, and fetches weather. "
        "For hard hikes near Calgary, set hard=True and radius_km≈50."
    ),
)

geocode_place_tool = StructuredTool.from_function(
    func=geocode_place,
    name="geocode_place",
    description=(
        "Geocode an Alberta place name (e.g., 'Calgary', 'Banff', 'Canmore') to coordinates. "
        "Use when the user gives a place name instead of lat/lon."
    ),
)

get_trails_near_tool = StructuredTool.from_function(
    func=get_trails_near,
    name="get_trails_near",
    description=(
        "Find hiking/running routes near coordinates. "
        "Inputs: lat, lon, radius_km (0.5–60), hard_only (bool for SAC T3+), natural_only (bool to exclude urban surfaces). "
        "Use radius_km≈50 for hard hikes near Calgary to include Kananaskis/Canmore."
    ),
)

get_trails_in_bbox_tool = StructuredTool.from_function(
    func=get_trails_in_bbox,
    name="get_trails_in_bbox",
    description="Find trails within a bounding box (min_lat, min_lon, max_lat, max_lon) in Alberta.",
)

get_weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description="Get trimmed hourly weather for the next N hours at given coordinates (America/Edmonton).",
)

weather_for_trail_tool = StructuredTool.from_function(
    func=weather_for_trail,
    name="weather_for_trail",
    description="Look up a trail name in Alberta (optionally with lat/lon) and return its coordinates plus a trimmed forecast.",
)

# --- LLM + Agent
# CHANGED: if possible, use gpt-4o-mini (better tool use). Fall back to gpt-3.5-turbo if needed.
llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")

def make_agent(return_steps: bool = False):
    return initialize_agent(
        tools=[
            recommend_near_place_tool,   # keep pipeline first
            geocode_place_tool,
            get_trails_near_tool,
            get_trails_in_bbox_tool,
            weather_for_trail_tool,
            get_weather_tool,
        ],
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        return_intermediate_steps=return_steps,   # NEW
        agent_kwargs={"system_message": SYSTEM_PROMPT},
    )

agent = make_agent(return_steps=DEBUG)

# --- Streamlit UI
st.set_page_config(page_title="TrailMate", layout="centered")
st.title("🥾 TrailMate: Hiking & Running Route Recommender")

query = st.text_input(
    "What kind of trail are you looking for?",
    placeholder="e.g., Hard hike ~2 hours near Calgary tomorrow"
)

if st.button("Get Recommendation") and query:
    with st.spinner("Thinking..."):
        if DEBUG:
            result = agent({"input": query})
            st.success("Here's what I found:")
            st.write(result["output"])
            with st.expander("Debug: intermediate steps"):
                st.write(result["intermediate_steps"])
        else:
            response = agent.run(query)
            st.success("Here's what I found:")
            st.write(response)
