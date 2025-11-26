from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import zipfile
from typing import Optional, List
from pathlib import Path
import tempfile
import json
import asyncio
import aiofiles
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DocumentSchema, SchemaStatus, SchemaModificationRequest, SchemaModificationResponse
from src.db.connection import init_db, db
from src.extractors.universal import extract_with_db_schema, extract_with_db_schema_openai
from src.extractors.schema_generator import generate_schema_from_documents, generate_schema_from_documents_openai
from src.extractors.classifier import classify_document_type, classify_document_type_openai
from src.config import MIN_CLASSIFICATION_CONFIDENCE, SUPPORTED_DOCUMENT_TYPES
from src.utils.schema_operations import (
    compare_schemas,
    apply_schema_modifications,
    calculate_next_version,
    generate_change_summary,
    validate_schema_modifications,
    get_modification_metadata,
    find_latest_schema_version
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Document Extraction API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.post("/extract")
async def extract_document(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Query for active schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                schema = active_result.scalar_one_or_none()

                # Query for in-review schema
                in_review_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.IN_REVIEW
                    )
                )
                in_review_result = await session.execute(in_review_schema_stmt)
                in_review_schema = in_review_result.scalar_one_or_none()

            if schema:
                extracted_data_json = await extract_with_db_schema(
                    document_paths=document_paths,
                    document_types=[doc.content_type for doc in document],
                    document_schema=schema
                )

                if not extracted_data_json:
                    raise HTTPException(
                        status_code=500,
                        detail="Extraction failed: No data returned from extraction service"
                    )

                extracted_data = json.loads(extracted_data_json)

                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "extracted",
                        "data": extracted_data,
                        "classification": {
                            "document_type": classification.document_type,
                            "country": classification.country,
                            "confidence": classification.confidence
                        },
                        "schema_used": {
                            "schema_id": str(schema.id),
                            "document_type": schema.document_type,
                            "country": schema.country,
                            "version": schema.version,
                            "status": schema.status,
                            "created_at": schema.created_at.isoformat(),
                            "updated_at": schema.updated_at.isoformat(),
                            "schema": schema.document_schema
                        }
                    }
                )

            if in_review_schema:
                return JSONResponse(
                    status_code=202,
                    content={
                        "status": "pending_review",
                        "message": "A schema for this document type is already awaiting approval.",
                        "classification": {
                            "document_type": classification.document_type,
                            "country": classification.country,
                            "confidence": classification.confidence
                        },
                        "schema": {
                            "schema_id": str(in_review_schema.id),
                            "document_type": in_review_schema.document_type,
                            "country": in_review_schema.country,
                            "version": in_review_schema.version,
                            "status": in_review_schema.status,
                            "created_at": in_review_schema.created_at.isoformat(),
                            "updated_at": in_review_schema.updated_at.isoformat(),
                            "schema": in_review_schema.document_schema
                        }
                    }
                )

            generated_schema = await generate_schema_from_documents(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_type=document_type,
                country=country
            )

            if not generated_schema:
                raise HTTPException(
                    status_code=500, detail="Failed to generate schema")

            schema_dict = {}
            for field_name, field_def in generated_schema.document_schema.items():
                if isinstance(field_def, dict):
                    schema_dict[field_name] = field_def
                else:
                    schema_dict[field_name] = {
                        "type": getattr(field_def, 'type', 'string'),
                        "description": getattr(field_def, 'description', ''),
                        "required": getattr(field_def, 'required', True),
                        "example": getattr(field_def, 'example', None)
                    }

            async with db.async_session_factory() as session:
                new_schema = DocumentSchema(
                    document_type=document_type,
                    country=country,
                    document_schema=schema_dict,
                    status=SchemaStatus.IN_REVIEW,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(new_schema)
                await session.commit()
                await session.refresh(new_schema)
                new_schema_id = new_schema.id

            return JSONResponse(
                status_code=201,
                content={
                    "status": "schema_generated",
                    "message": "Schema generated and saved for review Extraction not performed.",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "generated_schema": {
                        "document_type": generated_schema.document_type,
                        "country": generated_schema.country,
                        "confidence": generated_schema.confidence,
                        "schema": schema_dict
                    },
                    "schema_id": str(new_schema_id)
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed, {e}")


@app.get("/schemas")
async def get_all_schemas() -> JSONResponse:
    try:
        async with db.async_session_factory() as session:
            stmt = select(DocumentSchema)
            result = await session.execute(stmt)
            schemas = result.scalars().all()

            schema_list = []
            for schema in schemas:
                schema_list.append({
                    "id": str(schema.id),
                    "document_type": schema.document_type,
                    "country": schema.country,
                    "status": schema.status,
                    "version": schema.version,
                    "created_at": schema.created_at.isoformat(),
                    "updated_at": schema.updated_at.isoformat(),
                    "schema": schema.document_schema
                })

            return JSONResponse(
                status_code=200,
                content={
                    "schemas": schema_list,
                    "total_count": len(schema_list)
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve schemas: {e}")


@app.put("/schemas/{schema_id}/approve")
async def approve_schema(schema_id: str) -> JSONResponse:
    try:
        async with db.async_session_factory() as session:
            # Get the schema to approve
            stmt = select(DocumentSchema).where(DocumentSchema.id == uuid.UUID(schema_id))
            result = await session.execute(stmt)
            schema = result.scalar_one_or_none()
            
            if not schema:
                raise HTTPException(status_code=404, detail="Schema not found")

            if schema.status != SchemaStatus.IN_REVIEW:
                raise HTTPException(
                    status_code=400,
                    detail="Schema must be in IN_REVIEW status to approve"
                )

            # Find existing active schema
            existing_active_stmt = select(DocumentSchema).where(
                and_(
                    DocumentSchema.document_type == schema.document_type,
                    DocumentSchema.country == schema.country,
                    DocumentSchema.status == SchemaStatus.ACTIVE
                )
            )
            existing_active_result = await session.execute(existing_active_stmt)
            existing_active = existing_active_result.scalar_one_or_none()

            deprecated_schema_info = None
            if existing_active:
                existing_active.status = SchemaStatus.DEPRECATED
                existing_active.updated_at = datetime.now(timezone.utc)
                deprecated_schema_info = {
                    "id": str(existing_active.id),
                    "version": existing_active.version
                }

            schema.status = SchemaStatus.ACTIVE
            schema.updated_at = datetime.now(timezone.utc)
            if existing_active:
                schema.version = existing_active.version + 1

            await session.commit()
            await session.refresh(schema)

            await session.commit()
            await session.refresh(schema)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Schema approved successfully",
                "schema": {
                    "id": str(schema.id),
                    "document_type": schema.document_type,
                    "country": schema.country,
                    "status": schema.status,
                    "version": schema.version,
                    "created_at": schema.created_at.isoformat(),
                    "updated_at": schema.updated_at.isoformat(),
                    "schema": schema.document_schema
                },
                "deprecated_schema": deprecated_schema_info
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve schema: {e}")


@app.put("/schemas/{schema_id}/modify")
async def modify_schema(schema_id: str, request: SchemaModificationRequest) -> JSONResponse:
    try:
        async with db.async_session_factory() as session:
            stmt = select(DocumentSchema).where(DocumentSchema.id == uuid.UUID(schema_id))
            result = await session.execute(stmt)
            schema = result.scalar_one_or_none()
            
            if not schema:
                raise HTTPException(status_code=404, detail="Schema not found")

            latest_schema = await find_latest_schema_version(schema.document_type, schema.country)
            if not latest_schema or latest_schema.id != schema.id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot modify schema version, only the latest version can be modified. Latest schema ID: {str(latest_schema.id) if latest_schema else 'unknown'}"
                )

            is_valid, error_message = validate_schema_modifications(request.modifications)
            if not is_valid:
                raise HTTPException(
                    status_code=400, detail=f"Invalid modifications: {error_message}")

            original_schema = schema.document_schema.copy()
            modified_schema = apply_schema_modifications(
                original_schema, request.modifications)

            changes = compare_schemas(original_schema, modified_schema)

            if not changes:
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "No changes detected in the provided modifications",
                        "schema_id": schema_id,
                        "current_version": schema.version,
                        "original_schema": original_schema
                    }
                )

            next_version = await calculate_next_version(schema)

            change_summary = generate_change_summary(changes)
            modification_metadata = get_modification_metadata(
                changes, request.change_description)

            schema.status = SchemaStatus.DEPRECATED
            schema.updated_at = datetime.now(timezone.utc)

            new_schema = DocumentSchema(
                document_type=schema.document_type,
                country=schema.country,
                document_schema=modified_schema,
                status=SchemaStatus.IN_REVIEW,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                version=next_version
            )

            session.add(new_schema)
            await session.commit()
            await session.refresh(new_schema)

        response = SchemaModificationResponse(
            schema_id=str(new_schema.id),
            current_version=schema.version,
            proposed_version=next_version,
            changes=[change.model_dump() for change in changes],
            original_schema=original_schema,
            modified_schema=modified_schema,
            change_summary=change_summary,
            modification_metadata=modification_metadata
        )

        return JSONResponse(
            status_code=201,
            content={
                "status": "schema_modified",
                "message": "Schema successfully modified and saved",
                "original_schema_info": {
                    "id": str(schema.id),
                    "document_type": schema.document_type,
                    "country": schema.country,
                    "version": schema.version,
                    "status": schema.status,
                    "created_at": schema.created_at.isoformat(),
                    "updated_at": schema.updated_at.isoformat(),
                    "schema": schema.document_schema
                },
                "new_schema_info": {
                    "id": str(new_schema.id),
                    "document_type": new_schema.document_type,
                    "country": new_schema.country,
                    "status": new_schema.status,
                    "version": new_schema.version,
                    "created_at": new_schema.created_at.isoformat(),
                    "updated_at": new_schema.updated_at.isoformat(),
                    "schema": new_schema.document_schema
                },
                "modification_details": response.model_dump(),
                "note": "Changes have been saved to the database"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to apply schema modification: {e}")


@app.delete("/schemas/{schema_id}")
async def delete_schema(schema_id: str) -> JSONResponse:
    """Delete a schema by ID"""
    try:
        async with db.async_session_factory() as session:
            stmt = select(DocumentSchema).where(DocumentSchema.id == uuid.UUID(schema_id))
            result = await session.execute(stmt)
            schema = result.scalar_one_or_none()
            
            if not schema:
                raise HTTPException(status_code=404, detail="Schema not found")
            
            # Store schema info before deletion for response
            schema_info = {
                "id": str(schema.id),
                "document_type": schema.document_type,
                "country": schema.country,
                "status": schema.status,
                "version": schema.version,
                "created_at": schema.created_at.isoformat(),
                "updated_at": schema.updated_at.isoformat(),
                "schema": schema.document_schema
            }
            
            # Delete the schema
            await session.delete(schema)
            await session.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Schema deleted successfully",
                "deleted_schema": schema_info
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete schema: {e}")


@app.post("/register-schema")
async def register_schema(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    """
    Register a new document schema without extraction.
    Returns error if schema already exists in IN_REVIEW or ACTIVE status.
    """
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Check for existing active schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                active_schema = active_result.scalar_one_or_none()

                if active_schema:
                    raise HTTPException(                        status_code=409,
                        detail={
                            "error": "Schema already exists",
                            "message": f"An approved schema already exists for {document_type} from {country}",
                            "existing_schema": {
                                "schema_id": str(active_schema.id),
                                "document_type": active_schema.document_type,
                                "country": active_schema.country,
                                "version": active_schema.version,
                                "status": active_schema.status,
                                "created_at": active_schema.created_at.isoformat(),
                                "updated_at": active_schema.updated_at.isoformat()
                            }
                        }
                    )

                # Check for existing in-review schema
                in_review_schema_stmt = select(DocumentSchema).where(
                    and_(                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.IN_REVIEW
                    )
                )
                in_review_result = await session.execute(in_review_schema_stmt)
                in_review_schema = in_review_result.scalar_one_or_none()

                if in_review_schema:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "Schema already in review",
                            "message": f"A schema for {document_type} from {country} is already awaiting approval",
                            "existing_schema": {
                                "schema_id": str(in_review_schema.id),
                                "document_type": in_review_schema.document_type,
                                "country": in_review_schema.country,
                                "version": in_review_schema.version,
                                "status": in_review_schema.status,
                                "created_at": in_review_schema.created_at.isoformat(),
                                "updated_at": in_review_schema.updated_at.isoformat()
                            }
                        }
                    )

            # Generate new schema
            generated_schema = await generate_schema_from_documents(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_type=document_type,
                country=country
            )

            if not generated_schema:
                raise HTTPException(
                    status_code=500, detail="Failed to generate schema")

            schema_dict = {}
            for field_name, field_def in generated_schema.document_schema.items():
                if isinstance(field_def, dict):
                    schema_dict[field_name] = field_def
                else:
                    schema_dict[field_name] = {
                        "type": getattr(field_def, 'type', 'string'),
                        "description": getattr(field_def, 'description', ''),
                        "required": getattr(field_def, 'required', True),
                        "example": getattr(field_def, 'example', None)
                    }

            async with db.async_session_factory() as session:
                new_schema = DocumentSchema(
                    document_type=document_type,
                    country=country,
                    document_schema=schema_dict,
                    status=SchemaStatus.IN_REVIEW,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(new_schema)
                await session.commit()
                await session.refresh(new_schema)
                new_schema_id = new_schema.id

            return JSONResponse(
                status_code=201,
                content={
                    "status": "schema_registered",
                    "message": "Schema successfully registered and saved for review",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "generated_schema": {
                        "schema_id": str(new_schema_id),
                        "document_type": document_type,
                        "country": country,
                        "confidence": generated_schema.confidence,
                        "schema": schema_dict,
                        "status": SchemaStatus.IN_REVIEW,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Schema registration failed: {e}")


@app.post("/extract-with-approved-schema")
async def extract_with_approved_schema(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    """
    Extract data from documents using only ACTIVE (approved) schemas.
    Returns error if schema doesn't exist or is IN_REVIEW.
    """
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Query ONLY for active (approved) schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                schema = active_result.scalar_one_or_none()

                if not schema:
                    # Check if there's an in-review schema
                    in_review_schema_stmt = select(DocumentSchema).where(
                        and_(
                            DocumentSchema.document_type == document_type,
                            DocumentSchema.country == country,
                            DocumentSchema.status == SchemaStatus.IN_REVIEW
                        )
                    )
                    in_review_result = await session.execute(in_review_schema_stmt)
                    in_review_schema = in_review_result.scalar_one_or_none()

                    if in_review_schema:
                        raise HTTPException(
                            status_code=403,
                            detail={
                                "error": "Schema not approved",
                                "message": f"Schema for {document_type} from {country} is still in review and not approved for extraction",
                                "schema_info": {
                                    "schema_id": str(in_review_schema.id),
                                    "document_type": in_review_schema.document_type,
                                    "country": in_review_schema.country,
                                    "status": in_review_schema.status,
                                    "version": in_review_schema.version,
                                    "created_at": in_review_schema.created_at.isoformat()
                                }
                            }
                        )
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "error": "Schema not found",
                                "message": f"No approved schema exists for {document_type} from {country}",
                                "classification": {
                                    "document_type": classification.document_type,
                                    "country": classification.country,
                                    "confidence": classification.confidence
                                }
                            }
                        )

            # Extract data using the approved schema
            extracted_data_json = await extract_with_db_schema(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_schema=schema
            )

            extracted_data = json.loads(extracted_data_json)

            return JSONResponse(
                status_code=200,
                content={
                    "status": "extracted",
                    "data": extracted_data,
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "schema_used": {
                        "schema_id": str(schema.id),
                        "document_type": schema.document_type,
                        "country": schema.country,
                        "version": schema.version,
                        "status": schema.status,
                        "created_at": schema.created_at.isoformat(),
                        "updated_at": schema.updated_at.isoformat(),
                        "schema": schema.document_schema
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.post("/openai/extract")
async def extract_document_openai(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type_openai(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Query for active schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                schema = active_result.scalar_one_or_none()

                # Query for in-review schema
                in_review_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.IN_REVIEW
                    )
                )
                in_review_result = await session.execute(in_review_schema_stmt)
                in_review_schema = in_review_result.scalar_one_or_none()

            if schema:
                extracted_data_json = await extract_with_db_schema_openai(
                    document_paths=document_paths,
                    document_types=[doc.content_type for doc in document],
                    document_schema=schema
                )

                if not extracted_data_json:
                    raise HTTPException(
                        status_code=500,
                        detail="Extraction failed: No data returned from extraction service"
                    )

                extracted_data = json.loads(extracted_data_json)

                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "extracted",
                        "data": extracted_data,
                        "classification": {
                            "document_type": classification.document_type,
                            "country": classification.country,
                            "confidence": classification.confidence
                        },
                        "schema_used": {
                            "schema_id": str(schema.id),
                            "document_type": schema.document_type,
                            "country": schema.country,
                            "version": schema.version,
                            "status": schema.status,
                            "created_at": schema.created_at.isoformat(),
                            "updated_at": schema.updated_at.isoformat(),
                            "schema": schema.document_schema
                        }
                    }
                )

            if in_review_schema:
                return JSONResponse(
                    status_code=202,
                    content={
                        "status": "pending_review",
                        "message": "A schema for this document type is already awaiting approval.",
                        "classification": {
                            "document_type": classification.document_type,
                            "country": classification.country,
                            "confidence": classification.confidence
                        },
                        "schema": {
                            "schema_id": str(in_review_schema.id),
                            "document_type": in_review_schema.document_type,
                            "country": in_review_schema.country,
                            "version": in_review_schema.version,
                            "status": in_review_schema.status,
                            "created_at": in_review_schema.created_at.isoformat(),
                            "updated_at": in_review_schema.updated_at.isoformat(),
                            "schema": in_review_schema.document_schema
                        }
                    }
                )

            generated_schema = await generate_schema_from_documents_openai(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_type=document_type,
                country=country
            )

            if not generated_schema:
                raise HTTPException(
                    status_code=500, detail="Failed to generate schema")

            schema_dict = {}
            for field_name, field_def in generated_schema.document_schema.items():
                if isinstance(field_def, dict):
                    schema_dict[field_name] = field_def
                else:
                    schema_dict[field_name] = {
                        "type": getattr(field_def, 'type', 'string'),
                        "description": getattr(field_def, 'description', ''),
                        "required": getattr(field_def, 'required', True),
                        "example": getattr(field_def, 'example', None)
                    }

            async with db.async_session_factory() as session:
                new_schema = DocumentSchema(
                    document_type=document_type,
                    country=country,
                    document_schema=schema_dict,
                    status=SchemaStatus.IN_REVIEW,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(new_schema)
                await session.commit()
                await session.refresh(new_schema)
                new_schema_id = new_schema.id

            return JSONResponse(
                status_code=201,
                content={
                    "status": "schema_generated",
                    "message": "Schema generated and saved for review Extraction not performed.",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "generated_schema": {
                        "document_type": generated_schema.document_type,
                        "country": generated_schema.country,
                        "confidence": generated_schema.confidence,
                        "schema": schema_dict
                    },
                    "schema_id": str(new_schema_id)
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed, {e}")


@app.post("/openai/register-schema")
async def register_schema_openai(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    """
    Register a new document schema without extraction using OpenAI.
    Returns error if schema already exists in IN_REVIEW or ACTIVE status.
    """
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type_openai(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Check for existing active schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                active_schema = active_result.scalar_one_or_none()

                if active_schema:
                    raise HTTPException(                        status_code=409,
                        detail={
                            "error": "Schema already exists",
                            "message": f"An approved schema already exists for {document_type} from {country}",
                            "existing_schema": {
                                "schema_id": str(active_schema.id),
                                "document_type": active_schema.document_type,
                                "country": active_schema.country,
                                "version": active_schema.version,
                                "status": active_schema.status,
                                "created_at": active_schema.created_at.isoformat(),
                                "updated_at": active_schema.updated_at.isoformat()
                            }
                        }
                    )

                # Check for existing in-review schema
                in_review_schema_stmt = select(DocumentSchema).where(
                    and_(                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.IN_REVIEW
                    )
                )
                in_review_result = await session.execute(in_review_schema_stmt)
                in_review_schema = in_review_result.scalar_one_or_none()

                if in_review_schema:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "Schema already in review",
                            "message": f"A schema for {document_type} from {country} is already awaiting approval",
                            "existing_schema": {
                                "schema_id": str(in_review_schema.id),
                                "document_type": in_review_schema.document_type,
                                "country": in_review_schema.country,
                                "version": in_review_schema.version,
                                "status": in_review_schema.status,
                                "created_at": in_review_schema.created_at.isoformat(),
                                "updated_at": in_review_schema.updated_at.isoformat()
                            }
                        }
                    )

            # Generate new schema
            generated_schema = await generate_schema_from_documents_openai(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_type=document_type,
                country=country
            )

            if not generated_schema:
                raise HTTPException(
                    status_code=500, detail="Failed to generate schema")

            schema_dict = {}
            for field_name, field_def in generated_schema.document_schema.items():
                if isinstance(field_def, dict):
                    schema_dict[field_name] = field_def
                else:
                    schema_dict[field_name] = {
                        "type": getattr(field_def, 'type', 'string'),
                        "description": getattr(field_def, 'description', ''),
                        "required": getattr(field_def, 'required', True),
                        "example": getattr(field_def, 'example', None)
                    }

            async with db.async_session_factory() as session:
                new_schema = DocumentSchema(
                    document_type=document_type,
                    country=country,
                    document_schema=schema_dict,
                    status=SchemaStatus.IN_REVIEW,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(new_schema)
                await session.commit()
                await session.refresh(new_schema)
                new_schema_id = new_schema.id

            return JSONResponse(
                status_code=201,
                content={
                    "status": "schema_registered",
                    "message": "Schema successfully registered and saved for review",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "generated_schema": {
                        "schema_id": str(new_schema_id),
                        "document_type": document_type,
                        "country": country,
                        "confidence": generated_schema.confidence,
                        "schema": schema_dict,
                        "status": SchemaStatus.IN_REVIEW,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Schema registration failed: {e}")


@app.post("/openai/extract-with-approved-schema")
async def extract_with_approved_schema_openai(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    """
    Extract data from documents using only ACTIVE (approved) schemas using OpenAI.
    Returns error if schema doesn't exist or is IN_REVIEW.
    """
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            classification = await asyncio.wait_for(
                classify_document_type_openai(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            async with db.async_session_factory() as session:
                # Query ONLY for active (approved) schema
                active_schema_stmt = select(DocumentSchema).where(
                    and_(
                        DocumentSchema.document_type == document_type,
                        DocumentSchema.country == country,
                        DocumentSchema.status == SchemaStatus.ACTIVE
                    )
                )
                active_result = await session.execute(active_schema_stmt)
                schema = active_result.scalar_one_or_none()

                if not schema:
                    # Check if there's an in-review schema
                    in_review_schema_stmt = select(DocumentSchema).where(
                        and_(
                            DocumentSchema.document_type == document_type,
                            DocumentSchema.country == country,
                            DocumentSchema.status == SchemaStatus.IN_REVIEW
                        )
                    )
                    in_review_result = await session.execute(in_review_schema_stmt)
                    in_review_schema = in_review_result.scalar_one_or_none()

                    if in_review_schema:
                        raise HTTPException(
                            status_code=403,
                            detail={
                                "error": "Schema not approved",
                                "message": f"Schema for {document_type} from {country} is still in review and not approved for extraction",
                                "schema_info": {
                                    "schema_id": str(in_review_schema.id),
                                    "document_type": in_review_schema.document_type,
                                    "country": in_review_schema.country,
                                    "status": in_review_schema.status,
                                    "version": in_review_schema.version,
                                    "created_at": in_review_schema.created_at.isoformat()
                                }
                            }
                        )
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "error": "Schema not found",
                                "message": f"No approved schema exists for {document_type} from {country}",
                                "classification": {
                                    "document_type": classification.document_type,
                                    "country": classification.country,
                                    "confidence": classification.confidence
                                }
                            }
                        )

            # Extract data using the approved schema
            extracted_data_json = await extract_with_db_schema_openai(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_schema=schema
            )

            extracted_data = json.loads(extracted_data_json)

            return JSONResponse(
                status_code=200,
                content={
                    "status": "extracted",
                    "data": extracted_data,
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "schema_used": {
                        "schema_id": str(schema.id),
                        "document_type": schema.document_type,
                        "country": schema.country,
                        "version": schema.version,
                        "status": schema.status,
                        "created_at": schema.created_at.isoformat(),
                        "updated_at": schema.updated_at.isoformat(),
                        "schema": schema.document_schema
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.post("/openai/create-schema")
async def create_schema_openai(
    document: List[UploadFile] = File(...)
) -> JSONResponse:
    """
    Create a schema definition from a document that can be used to initialize the database using OpenAI.
    Returns a JSON format compatible with the schema initializer.
    """
    if not document or len(document) == 0:
        raise HTTPException(
            status_code=400, detail="At least one document file is required")

    for i, doc_file in enumerate(document):
        if doc_file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Document {i+1} must be JPEG, PNG, or PDF. Got: {doc_file.content_type}")
        
        if not doc_file.filename or doc_file.filename.strip() == "":
            raise HTTPException(
                status_code=400, detail=f"Document {i+1} filename is invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        try:
            for i, doc_file in enumerate(document):
                doc_path = temp_path / f"document_{i}_{uuid.uuid4()}"
                async with aiofiles.open(doc_path, "wb") as buffer:
                    content = await doc_file.read()
                    await buffer.write(content)
                document_paths.append(doc_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save documents: {e}")

        try:
            # Classify the document to get type and country
            classification = await asyncio.wait_for(
                classify_document_type_openai(document_paths, [doc.content_type for doc in document]),
                timeout=240.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail="Document classification timed out"
            )

        if not classification:
            raise HTTPException(
                status_code=400,
                detail="Unable to classify document type"
            )

        if classification.confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "classification_uncertain",
                    "message": "Document type classification confidence is below threshold",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "alternative_types": classification.alternative_types
                }
            )

        document_type = classification.document_type
        country = classification.country

        try:
            # Generate schema from the document
            generated_schema = await generate_schema_from_documents_openai(
                document_paths=document_paths,
                document_types=[doc.content_type for doc in document],
                document_type=document_type,
                country=country
            )

            if not generated_schema:
                raise HTTPException(
                    status_code=500, detail="Failed to generate schema")

            # Convert schema to proper format
            schema_dict = {}
            for field_name, field_def in generated_schema.document_schema.items():
                if isinstance(field_def, dict):
                    schema_dict[field_name] = field_def
                else:
                    schema_dict[field_name] = {
                        "type": getattr(field_def, 'type', 'string'),
                        "description": getattr(field_def, 'description', ''),
                        "required": getattr(field_def, 'required', True),
                        "example": getattr(field_def, 'example', None)
                    }

            # Create schema definition compatible with database initializer
            schema_definition = {
                "document_type": document_type,
                "country": country,
                "version": 1,
                "document_schema": schema_dict
            }

            return JSONResponse(
                status_code=200,
                content={
                    "status": "schema_created",
                    "message": "Schema successfully generated from document",
                    "classification": {
                        "document_type": classification.document_type,
                        "country": classification.country,
                        "confidence": classification.confidence
                    },
                    "schema_definition": schema_definition,
                    "usage_instructions": {
                        "description": "Save this schema_definition object as a JSON file in the schemas/ directory",
                        "filename_suggestion": f"{document_type.lower()}.json",
                        "example_usage": f"Save as schemas/{document_type.lower()}.json and restart the application to load it automatically"
                    }
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Schema creation failed: {e}")


@app.get("/")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Configure logging with app identifier
    logging.basicConfig(
        level=logging.INFO,
        format='[EXTRACTION-API] %(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    port = int(os.environ.get("PORT", 8005))
    print(f"[EXTRACTION-API] Starting Extraction API on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        workers=1,
        loop="asyncio",
        access_log=True,
        log_level="info"
    )
