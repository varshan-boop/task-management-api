# Task Management API

A backend-only REST API built with FastAPI and SQLite. It stores tasks locally
and provides interactive API documentation.

## Run

From the repository root:

```bash
pnpm --filter @workspace/api-server run dev
```

The server listens on `PORT` (8080 by default). The API is routed under `/api`.

- Interactive docs: `/api/docs`
- OpenAPI schema: `/api/openapi.json`
- Health check: `/api/healthz`
- Task collection: `/api/tasks`

SQLite data is written to `artifacts/api-server/data/tasks.sqlite3` by default.
Set `TASK_DATABASE_PATH` to use another file.

## Authentication

Register an account with a name, email address, and password. Passwords must be
at least 8 characters and no more than 72 UTF-8 bytes; they are stored as bcrypt
hashes, never as plain text. Registration returns the public user record.

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alex Example","email":"alex@example.com","password":"correct-horse-battery"}'
```

Log in to receive a signed JWT access token. Tokens expire after one hour.

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alex@example.com","password":"correct-horse-battery"}'
```

Set the returned `access_token` as a bearer token and include it in every task
request:

```bash
curl http://localhost:8080/api/tasks \
  -H 'Authorization: Bearer <access_token>'
```

The server signs JWTs with `JWT_SECRET`, or `SESSION_SECRET` if `JWT_SECRET` is
not set. Configure the signing key through environment variables. Registration and
login are public; task endpoints require authentication. Users can only access
their own tasks. A task owned by another user returns `403`; nonexistent tasks
return `404`. Previously stored tasks are retained during migration, but because
they have no owner they are not returned by authenticated task endpoints.

## Task fields

- `title` — required, 1–200 characters
- `description` — optional, up to 5,000 characters
- `status` — `todo`, `in_progress`, or `done` (defaults to `todo`)
- `due_date` — optional ISO date, such as `2026-10-15`
- `created_at` / `updated_at` — UTC timestamps returned by the API

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Register a user |
| `POST` | `/api/auth/login` | Log in and receive a JWT |
| `GET` | `/api/tasks` | List own tasks; supports `status`, `q`, `limit`, and `offset` |
| `POST` | `/api/tasks` | Create a task for the authenticated user |
| `GET` | `/api/tasks/{task_id}` | Get one of the authenticated user's tasks |
| `PATCH` | `/api/tasks/{task_id}` | Update one or more owned task fields |
| `DELETE` | `/api/tasks/{task_id}` | Delete an owned task |

Missing, invalid, or expired tokens return `401`. Invalid request data returns
`422`, duplicate registration returns `409`, a task owned by another user
returns `403`, and missing or legacy ownerless tasks return `404`.

### Examples

Create a task:

```bash
curl -X POST http://localhost:8080/api/tasks \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Prepare project plan","description":"Outline the first milestone","due_date":"2026-10-15"}'
```

Filter tasks by status and search text:

```bash
curl 'http://localhost:8080/api/tasks?status=todo&q=project&limit=20' \
  -H 'Authorization: Bearer <access_token>'
```

Update a task:

```bash
curl -X PATCH http://localhost:8080/api/tasks/1 \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"status":"in_progress"}'

## Live API

Deployed on Render: https://task-management-api-py7m.onrender.com

### Swagger Documentation

https://task-management-api-py7m.onrender.com/api/docs

### Health Check

https://task-management-api-py7m.onrender.com/api/healthz
```