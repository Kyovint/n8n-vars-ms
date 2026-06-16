from contextlib import asynccontextmanager
from typing import List

import psycopg2
from fastapi import FastAPI, HTTPException, status

from database import (
    ensure_table_exists,
    get_all_variables,
    get_connection,
    get_variable,
    insert_variable,
    resolve_schema,
    update_variable,
)
from models import (
    CreateVariableRequest,
    UpdateVariableRequest,
    VariableItem,
    VariableResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    conn.close()
    yield


app = FastAPI(title="n8n Variables MS", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/variables", response_model=VariableResponse, status_code=status.HTTP_201_CREATED)
def create_variable(req: CreateVariableRequest):
    schema = resolve_schema(req.environment)
    conn = get_connection()
    try:
        ensure_table_exists(conn, schema, req.project)
        insert_variable(conn, schema, req.project, req.name, req.value)
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Variable '{req.name}' already exists in project '{req.project}' ({req.environment})",
        )
    finally:
        conn.close()
    return VariableResponse(
        project=req.project,
        environment=req.environment,
        name=req.name,
        value=req.value,
    )


@app.get("/variables/{project}/{environment}/{name}", response_model=VariableItem)
def get_single_variable(project: str, environment: str, name: str):
    if environment not in ("dev", "test", "prod"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid environment")
    schema = resolve_schema(environment)
    conn = get_connection()
    try:
        row = get_variable(conn, schema, project, name)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variable '{name}' not found in project '{project}' ({environment})",
        )
    return VariableItem(**row)


@app.get("/variables/{project}/{environment}", response_model=List[VariableItem])
def get_project_variables(project: str, environment: str):
    if environment not in ("dev", "test", "prod"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid environment")
    schema = resolve_schema(environment)
    conn = get_connection()
    try:
        rows = get_all_variables(conn, schema, project)
    finally:
        conn.close()
    return [VariableItem(**r) for r in rows]


@app.put("/variables/{project}/{environment}/{name}", response_model=VariableResponse)
def update_variable_endpoint(project: str, environment: str, name: str, req: UpdateVariableRequest):
    if environment not in ("dev", "test", "prod"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid environment")
    schema = resolve_schema(environment)
    conn = get_connection()
    try:
        updated = update_variable(conn, schema, project, name, req.value)
    finally:
        conn.close()
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variable '{name}' not found in project '{project}' ({environment})",
        )
    return VariableResponse(
        project=project,
        environment=environment,
        name=name,
        value=req.value,
    )
