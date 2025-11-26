from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_
from ..db.models import SchemaChange, DocumentSchema
from ..db.connection import db


def compare_schemas(original_schema: Dict[str, Any], modified_schema: Dict[str, Any]) -> List[SchemaChange]:
    changes = []

    original_fields = set(original_schema.keys())
    modified_fields = set(modified_schema.keys())

    added_fields = modified_fields - original_fields
    for field_name in added_fields:
        changes.append(SchemaChange(
            change_type="field_added",
            field_name=field_name,
            old_value=None,
            new_value=modified_schema[field_name]
        ))

    removed_fields = original_fields - modified_fields
    for field_name in removed_fields:
        changes.append(SchemaChange(
            change_type="field_removed",
            field_name=field_name,
            old_value=original_schema[field_name],
            new_value=None
        ))

    common_fields = original_fields & modified_fields
    for field_name in common_fields:
        original_field = original_schema[field_name]
        modified_field = modified_schema[field_name]

        if original_field != modified_field:
            changes.append(SchemaChange(
                change_type="field_updated",
                field_name=field_name,
                old_value=original_field,
                new_value=modified_field
            ))

    return changes


def apply_schema_modifications(original_schema: Dict[str, Any], modifications: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    modified_schema = original_schema.copy()

    for field_name, field_definition in modifications.items():
        if field_definition is None:
            if field_name in modified_schema:
                del modified_schema[field_name]
        else:
            modified_schema[field_name] = field_definition

    return modified_schema


async def calculate_next_version(current_schema: DocumentSchema) -> int:
    async with db.async_session_factory() as session:
        stmt = select(DocumentSchema).where(
            and_(
                DocumentSchema.document_type == current_schema.document_type,
                DocumentSchema.country == current_schema.country
            )
        ).order_by(DocumentSchema.version.desc())
        
        result = await session.execute(stmt)
        latest_schema = result.scalars().first()

        if latest_schema:
            return latest_schema.version + 1
        else:
            return current_schema.version + 1


async def find_latest_schema_version(document_type: str, country: str) -> DocumentSchema:
    async with db.async_session_factory() as session:
        stmt = select(DocumentSchema).where(
            and_(
                DocumentSchema.document_type == document_type,
                DocumentSchema.country == country
            )
        ).order_by(DocumentSchema.version.desc())
        
        result = await session.execute(stmt)
        return result.scalars().first()


def generate_change_summary(changes: List[SchemaChange]) -> str:
    if not changes:
        return "No changes detected"

    summary_parts = []

    added_count = sum(1 for c in changes if c.change_type == "field_added")
    updated_count = sum(1 for c in changes if c.change_type == "field_updated")
    removed_count = sum(1 for c in changes if c.change_type == "field_removed")

    if added_count > 0:
        added_fields = [
            c.field_name for c in changes if c.change_type == "field_added"]
        summary_parts.append(
            f"Added {added_count} field(s): {', '.join(added_fields)}")

    if updated_count > 0:
        updated_fields = [
            c.field_name for c in changes if c.change_type == "field_updated"]
        summary_parts.append(
            f"Updated {updated_count} field(s): {', '.join(updated_fields)}")

    if removed_count > 0:
        removed_fields = [
            c.field_name for c in changes if c.change_type == "field_removed"]
        summary_parts.append(
            f"Removed {removed_count} field(s): {', '.join(removed_fields)}")

    return "; ".join(summary_parts)


def validate_schema_modifications(modifications: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[bool, str]:
    for field_name, field_definition in modifications.items():
        if field_definition is None:
            continue

        if not isinstance(field_definition, dict):
            return False, f"Field '{field_name}' definition must be a dictionary or None"

        if "type" not in field_definition:
            return False, f"Field '{field_name}' is missing required 'type' property"

        if "description" not in field_definition:
            return False, f"Field '{field_name}' is missing required 'description' property"

        valid_types = {"string", "integer",
                       "date", "boolean", "float", "number"}
        if field_definition["type"] not in valid_types:
            return False, f"Field '{field_name}' has invalid type '{field_definition['type']}'. Valid types: {valid_types}"

        if "required" in field_definition and not isinstance(field_definition["required"], bool):
            return False, f"Field '{field_name}' 'required' property must be a boolean"

    return True, ""


def get_modification_metadata(changes: List[SchemaChange], change_description: str = None) -> Dict[str, Any]:
    return {
        "modification_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_changes": len(changes),
        "change_types": {
            "added": len([c for c in changes if c.change_type == "field_added"]),
            "updated": len([c for c in changes if c.change_type == "field_updated"]),
            "removed": len([c for c in changes if c.change_type == "field_removed"])
        },
        "change_description": change_description or "No description provided",
        "affected_fields": [c.field_name for c in changes]
    }
