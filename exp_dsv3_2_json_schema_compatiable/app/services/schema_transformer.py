"""
JSON Schema transformer for DeepSeek compatibility.

Transforms standard JSON Schemas into DeepSeek Strict Mode compatible format
by automatically fixing common issues and removing unsupported features.
"""
import copy
from typing import Dict, Any
from app.utils.exceptions import DeepSeekSchemaTransformError


class DeepSeekSchemaTransformer:
    """Transforms JSON Schemas for DeepSeek Strict Mode compatibility."""

    # Attributes to remove by type
    ATTRIBUTES_TO_REMOVE = {
        "string": ["minLength", "maxLength"],
        "array": ["minItems", "maxItems"]
    }

    # Supported string formats in DeepSeek
    SUPPORTED_FORMATS = {
        "email", "hostname", "ipv4", "ipv6", "uuid"
    }

    def transform_for_strict_mode(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a schema to be DeepSeek Strict Mode compatible.

        Transformation rules:
        1. Auto-add required field for all object properties
        2. Set additionalProperties: false for objects
        3. Remove unsupported attributes (minLength, maxLength, etc.)
        4. Recursively transform nested objects

        Args:
            schema: Original JSON Schema

        Returns:
            Transformed schema

        Raises:
            DeepSeekSchemaTransformError: If transformation fails
        """
        try:
            transformed = copy.deepcopy(schema)
            self._transform_recursive(transformed)
            return transformed
        except Exception as e:
            raise DeepSeekSchemaTransformError(
                f"Failed to transform schema: {str(e)}"
            )

    def _transform_recursive(self, schema: Dict[str, Any]) -> None:
        """Recursively transform schema in place.

        Args:
            schema: Schema to transform (modified in place)
        """
        schema_type = schema.get("type")

        if not schema_type:
            return

        if schema_type == "object":
            self._transform_object(schema)
        elif schema_type == "string":
            self._transform_string(schema)
        elif schema_type == "array":
            self._transform_array(schema)
        elif schema_type in ("number", "integer", "boolean"):
            # No transformation needed for these types
            pass

        # Handle anyOf (union types)
        if "anyOf" in schema:
            for sub_schema in schema["anyOf"]:
                self._transform_recursive(sub_schema)

    def _transform_object(self, schema: Dict[str, Any]) -> None:
        """Transform object schema.

        1. Add all properties to required
        2. Set additionalProperties to false
        3. Recursively transform nested properties

        Args:
            schema: Object schema (modified in place)
        """
        properties = schema.get("properties", {})

        # Ensure all properties are required
        if properties:
            schema["required"] = list(properties.keys())

        # Force additionalProperties to false
        schema["additionalProperties"] = False

        # Recursively transform nested properties
        for prop_schema in properties.values():
            if isinstance(prop_schema, dict):
                self._transform_recursive(prop_schema)

    def _transform_string(self, schema: Dict[str, Any]) -> None:
        """Transform string schema by removing unsupported attributes.

        Args:
            schema: String schema (modified in place)
        """
        # Remove unsupported attributes
        for attr in self.ATTRIBUTES_TO_REMOVE.get("string", []):
            schema.pop(attr, None)

        # Remove unsupported format values
        format_value = schema.get("format")
        if format_value and format_value not in self.SUPPORTED_FORMATS:
            schema.pop("format", None)

    def _transform_array(self, schema: Dict[str, Any]) -> None:
        """Transform array schema by removing unsupported attributes.

        Args:
            schema: Array schema (modified in place)
        """
        # Remove unsupported attributes
        for attr in self.ATTRIBUTES_TO_REMOVE.get("array", []):
            schema.pop(attr, None)

        # Transform items schema if present
        items_schema = schema.get("items")
        if items_schema and isinstance(items_schema, dict):
            self._transform_recursive(items_schema)
