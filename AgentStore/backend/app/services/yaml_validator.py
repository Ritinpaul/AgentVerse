import json
import yaml
import jsonschema
from typing import Tuple, List, Dict, Any, Optional
from app.config import settings

def get_agent_schema() -> Dict[str, Any]:
    if not settings.SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {settings.SCHEMA_PATH}")
    with open(settings.SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_agent_yaml(yaml_str: str) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """Validates an agent.yaml string against the canonical schema.

    Returns:
        (is_valid, list_of_error_strings, parsed_yaml_dict)
    """
    errors: List[str] = []
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return False, [f"YAML Syntax Error: {str(e)}"], None

    if not isinstance(data, dict):
        return False, ["YAML must parse into a top-level JSON Object/Dictionary."], None

    try:
        schema = get_agent_schema()
        validator = jsonschema.Draft7Validator(schema)
        for error in validator.iter_errors(data):
            path = ".".join([str(p) for p in error.path]) if error.path else "root"
            errors.append(f"[{path}] {error.message}")
    except Exception as e:
        return False, [f"Schema Validation Error: {str(e)}"], None

    return len(errors) == 0, errors, data
