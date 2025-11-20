import json
import re
import ast
from typing import Dict, Any
import yaml


def parse_llm_string_to_dict(llm_output: str) -> Dict[str, Any]:
    s = llm_output.strip()

    json_match = re.search(r'\{.*\}', s, re.DOTALL)
    if json_match:
        s = json_match.group(0)
    else:
        raise ValueError("No JSON object found in the LLM output")

    s = s.strip()

    try:
        loaded = yaml.safe_load(s)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass

    try:
        loaded = ast.literal_eval(s)
        if isinstance(loaded, dict):
            return loaded
    except (ValueError, SyntaxError):
        pass

    try:
        # This regex finds single backslashes that are followed by common regex characters (d,s,w,D,S,W)
        # but are NOT already escaped (not preceded by another backslash)
        # It replaces them with double backslashes to properly escape them for JSON parsing.
        s_fixed = re.sub(r'(?<!\\)\\(?=[dswDSW])', r'\\\\', s)
        loaded = json.loads(s_fixed)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError as e:
        raise ValueError(
            "Failed to parse LLM output string into a dictionary") from e

    raise ValueError("All parsing strategies failed")
