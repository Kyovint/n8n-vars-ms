import psycopg2
from psycopg2 import sql
from config import settings


def get_connection():
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )


def resolve_schema(environment: str) -> str:
    return f"n8n_global_vars_{environment}"


def ensure_table_exists(conn, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "CREATE TABLE IF NOT EXISTS {}.{} "
                "(name TEXT PRIMARY KEY, value TEXT NOT NULL)"
            ).format(sql.Identifier(schema), sql.Identifier(table))
        )
    conn.commit()


def insert_variable(conn, schema: str, table: str, name: str, value: str) -> None:
    """Raises psycopg2.errors.UniqueViolation if name already exists."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("INSERT INTO {}.{} (name, value) VALUES (%s, %s)").format(
                sql.Identifier(schema), sql.Identifier(table)
            ),
            (name, value),
        )
    conn.commit()


def get_variable(conn, schema: str, table: str, name: str) -> dict | None:
    """Returns {"name": ..., "value": ...} or None if not found (including missing table)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT name, value FROM {}.{} WHERE name = %s").format(
                    sql.Identifier(schema), sql.Identifier(table)
                ),
                (name,),
            )
            row = cur.fetchone()
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return None
    if row is None:
        return None
    return {"name": row[0], "value": row[1]}


def get_all_variables(conn, schema: str, table: str) -> list[dict]:
    """Returns list of {"name": ..., "value": ...}. Returns [] if table doesn't exist."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT name, value FROM {}.{} ORDER BY name").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
            rows = cur.fetchall()
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return []
    return [{"name": r[0], "value": r[1]} for r in rows]


def update_variable(conn, schema: str, table: str, name: str, value: str) -> bool:
    """Returns True if updated, False if variable or table doesn't exist."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "UPDATE {}.{} SET value = %s WHERE name = %s"
                ).format(sql.Identifier(schema), sql.Identifier(table)),
                (value, name),
            )
            updated = cur.rowcount
        conn.commit()
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return False
    return updated > 0
