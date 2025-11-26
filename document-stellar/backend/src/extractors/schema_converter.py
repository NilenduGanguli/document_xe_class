from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, Field, create_model, ConfigDict
from datetime import datetime


def convert_db_schema_to_pydantic(document_schema: Dict[str, Any], document_type: str) -> Type[BaseModel]:
    fields = {}

    for field_name, field_definition in document_schema.items():
        field_type = field_definition.get("type", "str")
        description = field_definition.get("description", "")
        required = field_definition.get("required", True)

        python_type = _map_field_type(field_type)

        if not required:
            python_type = Optional[python_type]

        # For OpenAI Structured Outputs with strict=True, all fields must be required.
        # Optional fields should be nullable but the key must be present.
        fields[field_name] = (
            python_type, Field(..., description=description))

    fields['information_unreadable'] = (bool, Field(
        ..., description="True if any information is unreadable"))
    fields['is_document_correct'] = (bool, Field(
        ..., description="True if document matches expected type"))

    model_name = f"{document_type.title().replace('_', '')}ExtractionModel"
    
    model_config = ConfigDict(extra='forbid')

    return create_model(model_name, __config__=model_config, **fields)


def _map_field_type(field_type: str) -> Type:
    type_mapping = {
        "string": str,
        "str": str,
        "text": str,
        "integer": int,
        "int": int,
        "number": int,
        "float": float,
        "decimal": float,
        "boolean": bool,
        "bool": bool,
        "date": str,
        "datetime": datetime,
        "email": str,
        "phone": str,
        "url": str,
    }

    return type_mapping.get(field_type.lower(), str)
