import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()


# ─── LLM factory ──────────────────────────────────────────────────────────────

def get_llm(temperature: float = 0.7) -> ChatGroq:
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )


# ─── Recipe generation ────────────────────────────────────────────────────────

_RECIPE_SYSTEM = """You are Crave, a world-class AI chef. Your only job right now is to output JSON.

Return ONLY a valid JSON array containing exactly 3 recipe objects.
No markdown. No backticks. No explanation. No text before or after the array.

Each object must have exactly these keys:
{{
  "name":        "Recipe Name",
  "description": "Two-sentence appetizing description.",
  "cuisine":     "Cuisine type",
  "time":        "X mins",
  "difficulty":  "Easy" | "Medium" | "Hard",
  "calories":    "~XXX kcal",
  "servings":    "X servings",
  "protein":     "Xg",
  "carbs":       "Xg",
  "fat":         "Xg",
  "ingredients": ["qty ingredient", "..."],
  "steps":       ["Step description", "..."],
  "tip":         "One pro chef tip"
}}"""

_RECIPE_HUMAN = """Generate 3 recipes based on:
- Ingredients available: {ingredients}
- Dietary preferences: {diet}
- Cuisine type: {cuisine}
- Cooking time: {time}
- Difficulty: {difficulty}
- Special requests: {special}

Remember: return ONLY the JSON array, nothing else."""

_recipe_prompt = ChatPromptTemplate.from_messages([
    ("system", _RECIPE_SYSTEM),
    ("human",  _RECIPE_HUMAN),
])


def _extract_json_array(text: str) -> list:
    """Pull the first [...] block out of a string and parse it."""
    text = text.strip()
    # strip markdown fences if the model disobeyed
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # find the outermost [...] in case there is preamble text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def generate_recipes(
    ingredients: str,
    diet: list,
    cuisine: str,
    time: str,
    difficulty: str,
    special: str,
) -> list:
    """
    Call the LLM and return a list of 3 recipe dicts.
    Retries once with temperature=0 if the first response is not valid JSON.
    """
    payload = {
        "ingredients": ingredients or "any",
        "diet":        ", ".join(diet) if diet else "none",
        "cuisine":     cuisine     or "any",
        "time":        time        or "any",
        "difficulty":  difficulty  or "any",
        "special":     special     or "none",
    }

    # First attempt – creative temperature
    try:
        llm    = get_llm(temperature=0.8)
        chain  = _recipe_prompt | llm | StrOutputParser()
        raw    = chain.invoke(payload)
        return _extract_json_array(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Retry with temperature=0 for a more deterministic response
    llm   = get_llm(temperature=0)
    chain = _recipe_prompt | llm | StrOutputParser()
    raw   = chain.invoke(payload)
    return _extract_json_array(raw)


# ─── Chef chat ────────────────────────────────────────────────────────────────

_CHEF_SYSTEM = """You are Crave, a warm and knowledgeable AI chef assistant.
You specialize in recipes, cooking techniques, ingredient substitutions, nutrition, and food pairings.
Be concise, friendly, and practical. Use occasional food emojis.
Keep responses under 150 words unless the user explicitly asks for a full recipe."""


def chat_with_chef(history: list, user_message: str) -> str:
    """
    Send the full conversation history plus the new user message to the LLM
    and return the assistant's reply as a plain string.

    history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    llm = get_llm(temperature=0.7)

    messages = [SystemMessage(content=_CHEF_SYSTEM)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    return response.content