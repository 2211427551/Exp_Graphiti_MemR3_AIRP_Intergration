"""
JSON Schema validator for DeepSeek Strict Mode requirements.

Validates that JSON schemas comply with DeepSeek's strict mode constraints
as documented in: https://api-docs.deepseek.com/guides/tool_calls
"""
from typing import Tuple, List, Dict, Any
from app.utils.exceptions import DeepSeekValidationError


class DeepSeekSchemaValidator:
    """Validates JSON Schema for DeepSeek Strict Mode compatibility."""

    # Supported string formats
    SUPPORTED_STRING_FORMATS = {
        "email", "hostname", "ipv4", "ipv6", "uuid"
    }

    # Unsupported attributes by type
    UNSUPPORTED_ATTRIBUTES = {
        "string": ["minLength", "maxLength"],
        "array": ["minItems", "maxItems"]
    }

    def validate_schema(self, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a JSON schema against DeepSeek requirements.

        Args:
            schema: JSON Schema dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        errors.extend(self._validate_schema_recursive(schema, ""))

        return len(errors) == 0, errors

    def _validate_schema_recursive(
        self, schema: Dict[str, Any], path: str
    ) -> List[str]:
        """Recursively validate schema and all nested schemas.

        Args:
            schema: Schema to validate
            path: Current path in schema (for error messages)

        Returns:
            List of validation errors
        """
        errors = []
        schema_type = schema.get("type")

        if not schema_type:
            return errors  # No type to validate

        if schema_type == "object":
            errors.extend(self._validate_object(schema, path))
        elif schema_type == "string":
            errors.extend(self._validate_string(schema, path))
        elif schema_type == "array":
            errors.extend(self._validate_array(schema, path))
        elif schema_type in ("number", "integer"):
            # Number types have minimal restrictions
            pass
        elif schema_type == "boolean":
            # Boolean has no additional constraints
            pass

        # Handle anyOf (union types)
        if "anyOf" in schema:
            for idx, sub_schema in enumerate(schema["anyOf"]):
                sub_errors = self._validate_schema_recursive(
                    sub_schema, f"{path}.anyOf[{idx}]"
                )
                errors.extend(sub_errors)

        return errors

    def _validate_object(self, schema: Dict[str, Any], path: str) -> List[str]:
        """Validate object type schema requirements.

        Args:
            schema: Object schema
            path: Schema path

        Returns:
            List of validation errors
        """
        errors = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_properties = schema.get("additionalProperties", True)

        # All properties must be required
        missing_required = set(properties.keys()) - set(required)
        if missing_required:
            errors.append(
                f"{path or 'root'}: All properties must be required. "
                f"Missing in 'required': {sorted(missing_required)}"
            )

        # additionalProperties must be false
        if additional_properties is not False:
            errors.append(
                f"{path or 'root'}: 'additionalProperties' must be false"
            )

        # Recursively validate nested properties
        for prop_name, prop_schema in properties.items():
            sub_errors = self._validate_schema_recursive(
                prop_schema, f"{path}.{prop_name}" if path else prop_name
            )
            errors.extend(sub_errors)

        return errors

    def _validate_string(self, schema: Dict[str, Any], path: str) -> List[str]:
        """Validate string type schema requirements.

        Args:
            schema: String schema
            path: Schema path

        Returns:
            List of validation errors
        """
        errors = []

        # Check for unsupported attributes
        for attr in self.UNSUPPORTED_ATTRIBUTES.get("string", []):
            if attr in schema:
                errors.append(
                    f"{path or 'root'}: String type does not support '{attr}'"
                )

        # Validate format if present
        format_value = schema.get("format")
        if format_value and format_value not in self.SUPPORTED_STRING_FORMATS:
            errors.append(
                f"{path or 'root'}: Unsupported format '{format_value}'. "
                f"Supported formats: {sorted(self.SUPPORTED_STRING_FORMATS)}"
            )

        return errors

    def _validate_array(self, schema: Dict[str, Any], path: str) -> List[str]:
        """Validate array type schema requirements.

        Args:
            schema: Array schema
            path: Schema path

        Returns:
            List of validation errors
        """
        errors = []

        # Check for unsupported attributes
        for attr in self.UNSUPPORTED_ATTRIBUTES.get("array", []):
            if attr in schema:
                errors.append(
                    f"{path or 'root'}: Array type does not support '{attr}'"
                )

        # Validate items schema if present
        items_schema = schema.get("items")
        if items_schema and isinstance(items_schema, dict):
            sub_errors = self._validate_schema_recursive(
                items_schema, f"{path}.items" if path else "items"
            )
            errors.extend(sub_errors)

        return errors
