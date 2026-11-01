# Brakwater Boats workspace

Workspace for the Brakwater Boats case. It contains a sandbox of the Keelson ERP API with realistic test data, the open orders export the purchasing team uses today, and an empty agent to build your solution in.

All companies, people and data are fictional.

## Structure

```
docker-compose.yml     starts the API and the agent
keelson-api/           Keelson ERP API (sandbox, read only)
agent/                 client, rules, the current export, and agent.py for your solution
docs/API.md            API documentation
```

## Getting started

```bash
docker compose up -d keelson-api                          # start the API on http://localhost:8000
curl http://localhost:8000/health                         # check it runs

docker compose run --rm agent python export_open_orders.py   # run the current export
docker compose run --rm agent python agent.py                # run your agent
```

The API reloads automatically when you change its code. The `agent` folder is mounted into its container, so changes there are picked up on the next run.

## Tests

```bash
docker compose run --rm keelson-api pytest
docker compose run --rm agent pytest
```

## Environment

1. Copy `.env.example` to `.env` and add the LLM API key you were given. It is passed to the agent container.
2. The API uses today as business date. All dates in the sandbox data are relative to it.
