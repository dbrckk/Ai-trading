# Cloudflare paper scheduler

This Worker is the external five-minute trigger for the `Ai-trading` paper executor. It contains no trading logic, model state, or database credential.

## Cloudflare configuration

- Worker name: `ai-trading-paper-scheduler`
- GitHub repository: `dbrckk/Ai-trading`
- Workers Builds root directory: `infra/cloudflare-paper-scheduler`
- Non-secret variable `TARGET_URL` is committed in `wrangler.toml` and points to the Render `/internal/paper-cycle` endpoint.
- Secret binding `SCHEDULER_TOKEN` must be created in Cloudflare as a **Secret**. Never put its value in `wrangler.toml`, Git, logs, issues, or chat.
- The Cron Trigger is managed by `wrangler.toml` and is `*/5 * * * *` in UTC. Do not create a duplicate manual trigger if the Wrangler-managed trigger already exists.

Cloudflare does not receive `AI_TRADING_DATABASE_URL`, Neon credentials, symbols, intervals, risk settings, or order instructions. Its only job is to send an authenticated POST to Render.

Each request also sends the fixed non-secret header `X-Scheduler-Source: cloudflare`. Render emits one sanitized app-log event after handling the request, for example:

```json
{"event":"scheduler_request","ok":true,"processed":1,"source":"cloudflare","status_code":200}
```

The telemetry never includes the Authorization header, scheduler token, request body/query, database URL, or provider credentials. Three consecutive `source=cloudflare`, `ok=true`, `status_code=200` events provide the production delivery evidence required by issue #40.

## Tests

The Worker uses only Node built-ins for its test harness:

```bash
npm test
```

No dependency installation is required.

## Rollback

Disable the Cloudflare Cron Trigger. Keep Render in external-scheduler mode and use the repository's GitHub Actions `workflow_dispatch` paper cycle as the manual fallback while diagnosing.
