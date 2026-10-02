from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Iterator

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "data" / "tasks.sqlite3"
DATABASE_PATH = Path(os.environ.get("TASK_DATABASE_PATH", DEFAULT_DATABASE_PATH))
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "task-management-api"
JWT_ACCESS_TOKEN_TTL = timedelta(hours=1)
JWT_ACCESS_TOKEN_TTL_SECONDS = int(JWT_ACCESS_TOKEN_TTL.total_seconds())
BCRYPT_ROUNDS = 12


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must contain at least one non-space character.")
        return value


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title must contain at least one non-space character.")
        return value


class TaskRecord(TaskCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class UserEmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class UserRegistration(UserEmailInput):
    name: str = Field(min_length=1, max_length=120)
    password: SecretStr

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must contain at least one non-space character.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value


class UserLogin(UserEmailInput):
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value


class UserRecord(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET") or os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError(
            "Configure JWT_SECRET or SESSION_SECRET in the environment before starting the API."
        )
    return secret


def get_db() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK (status IN ('todo', 'in_progress', 'done')),
                due_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        if "user_id" not in task_columns:
            # Keep pre-authentication rows intact; they have no account owner and
            # therefore remain hidden from the authenticated task endpoints.
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status)"
        )
        connection.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_jwt_secret()
    initialize_database()
    yield


bearer_scheme = HTTPBearer(
    scheme_name="JWTBearer",
    bearerFormat="JWT",
    description="Paste the access token returned by POST /api/auth/login.",
    auto_error=False,
)


app = FastAPI(
    title="Task Management API",
    description=(
        "A backend-only REST API for creating, organizing, and tracking tasks. "
        "Task status can be `todo`, `in_progress`, or `done`."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

DbConnection = Annotated[sqlite3.Connection, Depends(get_db)]


def user_from_row(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        created_at=row["created_at"],
    )


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + JWT_ACCESS_TOKEN_TTL,
            "type": "access",
        },
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: DbConnection,
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    try:
        claims = jwt.decode(
            credentials.credentials,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "iss", "iat", "exp", "type"]},
        )
        user_id_claim = claims["sub"]
        if claims["type"] != "access" or not user_id_claim.isdigit():
            raise unauthorized()
        user_id = int(user_id_claim)
    except (jwt.PyJWTError, KeyError, AttributeError, ValueError):
        raise unauthorized() from None

    row = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise unauthorized()
    return user_from_row(row)


CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


def serialize_task(row: sqlite3.Row) -> dict[str, object]:
    task = dict(row)
    task.pop("user_id", None)
    return task


def require_task_access(
    task_id: int,
    user_id: int,
    db: sqlite3.Connection,
) -> sqlite3.Row:
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None or row["user_id"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this task.",
        )
    return row


@app.get("/api", include_in_schema=False)
@app.get("/api/", include_in_schema=False)
def api_info() -> dict[str, str]:
    return {
        "name": "Task Management API",
        "docs": "/api/docs",
        "health": "/api/healthz",
        "tasks": "/api/tasks",
    }


@app.post(
    "/api/auth/register",
    response_model=UserRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
def register_user(payload: UserRegistration, db: DbConnection) -> UserRecord:
    password_hash = bcrypt.hashpw(
        payload.password.get_secret_value().encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("ascii")
    try:
        cursor = db.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, str(payload.email), password_hash, utc_now()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None

    row = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return user_from_row(row)


@app.post("/api/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(payload: UserLogin, db: DbConnection) -> LoginResponse:
    row = db.execute(
        "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
        (str(payload.email),),
    ).fetchone()
    password = payload.password.get_secret_value().encode("utf-8")
    if row is None or not bcrypt.checkpw(password, row["password_hash"].encode("ascii")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginResponse(
        access_token=create_access_token(row["id"]),
        expires_in=JWT_ACCESS_TOKEN_TTL_SECONDS,
        user=user_from_row(row),
    )


@app.get("/api/healthz", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/tasks",
    response_model=TaskRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
)
def create_task(
    payload: TaskCreate,
    response: Response,
    db: DbConnection,
    current_user: CurrentUser,
):
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO tasks (user_id, title, description, status, due_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            current_user.id,
            payload.title.strip(),
            payload.description,
            payload.status.value,
            payload.due_date.isoformat() if payload.due_date else None,
            now,
            now,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    response.headers["Location"] = f"/api/tasks/{cursor.lastrowid}"
    return serialize_task(row)


@app.get("/api/tasks", response_model=list[TaskRecord], tags=["Tasks"])
def list_tasks(
    db: DbConnection,
    current_user: CurrentUser,
    task_status: Annotated[
        TaskStatus | None,
        Query(alias="status", description="Filter by task status."),
    ] = None,
    q: Annotated[
        str | None, Query(max_length=200, description="Search titles and descriptions.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    conditions: list[str] = ["user_id = ?"]
    parameters: list[object] = [current_user.id]
    if task_status is not None:
        conditions.append("status = ?")
        parameters.append(task_status.value)
    if q:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        search = f"%{q.strip()}%"
        parameters.extend((search, search))
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        f"""
        SELECT * FROM tasks
        {where_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (*parameters, limit, offset),
    ).fetchall()
    return [serialize_task(row) for row in rows]


@app.get("/api/tasks/{task_id}", response_model=TaskRecord, tags=["Tasks"])
def get_task(task_id: int, db: DbConnection, current_user: CurrentUser):
    row = require_task_access(task_id, current_user.id, db)
    return serialize_task(row)


@app.patch("/api/tasks/{task_id}", response_model=TaskRecord, tags=["Tasks"])
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: DbConnection,
    current_user: CurrentUser,
):
    require_task_access(task_id, current_user.id, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )
    if "title" in changes:
        if changes["title"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Task title cannot be null.",
            )
        changes["title"] = changes["title"].strip()
    if "status" in changes:
        if changes["status"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Task status cannot be null.",
            )
        changes["status"] = changes["status"].value
    if "due_date" in changes:
        changes["due_date"] = (
            changes["due_date"].isoformat() if changes["due_date"] else None
        )
    changes["updated_at"] = utc_now()

    assignments = ", ".join(f"{column} = ?" for column in changes)
    values = list(changes.values()) + [task_id]
    cursor = db.execute(
        f"UPDATE tasks SET {assignments} WHERE id = ? AND user_id = ?",
        values + [current_user.id],
    )
    if cursor.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return serialize_task(row)


@app.delete(
    "/api/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
)
def delete_task(task_id: int, db: DbConnection, current_user: CurrentUser) -> Response:
    require_task_access(task_id, current_user.id, db)
    cursor = db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, current_user.id),
    )
    if cursor.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)