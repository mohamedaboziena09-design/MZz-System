"""
Schema Loader
=============
Loads JSON schemas from the /schemas directory and validates
dictionaries against them using a built-in Draft-7 validator
(zero external dependencies — stdlib only).

Supported keywords
------------------
  type, required, properties, additionalProperties,
  enum, minLength, maxLength, minimum, maximum,
  pattern, format (date, email)

Usage
-----
    from src.schema_loader import SchemaLoader, SchemaValidationError

    try:
        SchemaLoader.validate_employee(data)
    except SchemaValidationError as exc:
        for msg in exc.errors:
            print(msg)
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "schemas"

# ── Basic format regexes ─────────────────────────────────────
_DATE_RE  = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+$"
)


# ── Exceptions ───────────────────────────────────────────────

class SchemaValidationError(Exception):
    """Raised when data fails JSON Schema validation.

    Attributes
    ----------
    errors : list[str]
        Human-readable list of validation error messages.
    """

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []

    def __str__(self) -> str:
        if self.errors:
            bullet_list = "\n  • ".join(self.errors)
            return f"{super().__str__()}\n  • {bullet_list}"
        return super().__str__()


# ── Lightweight Draft-7 validator ────────────────────────────

def _type_ok(value: Any, type_spec: Any) -> bool:
    """Return True if *value* matches *type_spec* (string or list of strings)."""
    types = type_spec if isinstance(type_spec, list) else [type_spec]
    for t in types:
        if t == "null"    and value is None:               return True
        if t == "string"  and isinstance(value, str):      return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool): return True
        if t == "number"  and isinstance(value, (int, float)) and not isinstance(value, bool): return True
        if t == "boolean" and isinstance(value, bool):     return True
        if t == "array"   and isinstance(value, list):     return True
        if t == "object"  and isinstance(value, dict):     return True
    return False


def _type_name(type_spec: Any) -> str:
    if isinstance(type_spec, list):
        return " or ".join(type_spec)
    return str(type_spec)


def _validate_value(
    value: Any,
    prop_schema: dict,
    field: str,
    errors: list[str],
) -> None:
    """Validate *value* against *prop_schema*, appending errors."""

    # null + missing optional → skip further checks
    if value is None:
        type_spec = prop_schema.get("type")
        if type_spec and not _type_ok(value, type_spec):
            errors.append(
                f"[{field}] expected {_type_name(type_spec)}, got null"
            )
        return

    # type check
    type_spec = prop_schema.get("type")
    if type_spec and not _type_ok(value, type_spec):
        errors.append(
            f"[{field}] expected {_type_name(type_spec)}, "
            f"got {type(value).__name__} ({value!r})"
        )
        return   # further checks would be noisy / irrelevant

    # enum
    if "enum" in prop_schema and value not in prop_schema["enum"]:
        errors.append(
            f"[{field}] must be one of {prop_schema['enum']!r}, got {value!r}"
        )

    # string-specific
    if isinstance(value, str):
        if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
            errors.append(
                f"[{field}] must be at least {prop_schema['minLength']} character(s) long "
                f"(got {len(value)})"
            )
        if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
            errors.append(
                f"[{field}] must be at most {prop_schema['maxLength']} character(s) long "
                f"(got {len(value)})"
            )
        if "pattern" in prop_schema and not re.match(prop_schema["pattern"], value):
            errors.append(
                f"[{field}] does not match pattern {prop_schema['pattern']!r}"
            )
        fmt = prop_schema.get("format")
        if fmt == "date" and not _DATE_RE.match(value):
            errors.append(
                f"[{field}] must be a date in YYYY-MM-DD format, got {value!r}"
            )
        if fmt == "email" and not _EMAIL_RE.match(value):
            errors.append(f"[{field}] must be a valid email address, got {value!r}")

    # numeric
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in prop_schema and value < prop_schema["minimum"]:
            errors.append(
                f"[{field}] must be >= {prop_schema['minimum']}, got {value}"
            )
        if "maximum" in prop_schema and value > prop_schema["maximum"]:
            errors.append(
                f"[{field}] must be <= {prop_schema['maximum']}, got {value}"
            )


def _validate_object(
    data: dict[str, Any],
    schema: dict,
    errors: list[str],
    path: str = "",
) -> None:
    """Recursively validate *data* (an object) against *schema*."""

    prefix = f"{path}." if path else ""

    # required
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"[{prefix}{field}] is required but missing")

    # additionalProperties
    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        extra   = set(data.keys()) - allowed
        for key in sorted(extra):
            errors.append(
                f"[{prefix}{key}] additional property is not allowed"
            )

    # properties
    for field, prop_schema in schema.get("properties", {}).items():
        if field not in data:
            continue   # handled by required check above
        _validate_value(data[field], prop_schema, f"{prefix}{field}", errors)


# ── SchemaLoader ─────────────────────────────────────────────

class SchemaLoader:
    """Loads and caches JSON schemas, then validates data against them."""

    _cache: dict[str, dict] = {}

    @classmethod
    def load(cls, schema_name: str) -> dict:
        """Load a schema by name (without .json extension).

        Schemas are cached after the first load.

        Raises
        ------
        FileNotFoundError
        """
        if schema_name not in cls._cache:
            schema_path = SCHEMAS_DIR / f"{schema_name}.json"
            if not schema_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {schema_path}\n"
                    f"Expected location: {SCHEMAS_DIR}"
                )
            with schema_path.open("r", encoding="utf-8") as fh:
                cls._cache[schema_name] = json.load(fh)
        return cls._cache[schema_name]

    @classmethod
    def validate(cls, schema_name: str, data: dict[str, Any]) -> None:
        """Validate *data* against the named schema.

        Raises
        ------
        SchemaValidationError
            If one or more validation rules are violated.
        """
        schema = cls.load(schema_name)
        errors: list[str] = []
        _validate_object(data, schema, errors)

        if errors:
            raise SchemaValidationError(
                f"Schema '{schema_name}' validation failed "
                f"with {len(errors)} error(s).",
                errors=errors,
            )

    @classmethod
    def validate_employee(cls, data: dict[str, Any]) -> None:
        """Validate employee data against ``schemas/employee.json``."""
        cls.validate("employee", data)

    @classmethod
    def validate_document(cls, data: dict[str, Any]) -> None:
        """Validate document data against ``schemas/document.json``."""
        cls.validate("document", data)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory schema cache (useful in tests)."""
        cls._cache.clear()
