"""
Helper utility functions.
"""
import hashlib
import json


def hash_schema(schema: dict) -> str:
    """Generate a hash for a JSON schema for caching purposes.

    Args:
        schema: JSON Schema dictionary

    Returns:
        SHA256 hash string
    """
    schema_str = json.dumps(schema, sort_keys=True)
    return hashlib.sha256(schema_str.encode()).hexdigest()


def merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with overriding values

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
