import assert from "node:assert/strict";
import test from "node:test";

import worker, { invokePaperCycle } from "../src/index.js";


test("invokePaperCycle sends only authenticated POST to configured target", async () => {
  const calls = [];
  const env = {
    TARGET_URL: "https://example.test/internal/paper-cycle",
    SCHEDULER_TOKEN: "scheduler-secret",
  };

  await invokePaperCycle(env, async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200 };
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, env.TARGET_URL);
  assert.equal(calls[0].options.method, "POST");
  assert.equal(
    calls[0].options.headers.Authorization,
    "Bearer scheduler-secret",
  );
  assert.equal(
    calls[0].options.headers["User-Agent"],
    "ai-trading-cloudflare-scheduler/1",
  );
  assert.equal(
    calls[0].options.headers["X-Scheduler-Source"],
    "cloudflare",
  );
  assert.equal("body" in calls[0].options, false);
});


test("invokePaperCycle rejects missing TARGET_URL without fetching", async () => {
  let fetches = 0;
  await assert.rejects(
    invokePaperCycle(
      { SCHEDULER_TOKEN: "scheduler-secret" },
      async () => {
        fetches += 1;
        return { ok: true, status: 200 };
      },
    ),
    { message: "scheduler configuration missing" },
  );
  assert.equal(fetches, 0);
});


test("invokePaperCycle rejects missing SCHEDULER_TOKEN without fetching", async () => {
  let fetches = 0;
  await assert.rejects(
    invokePaperCycle(
      { TARGET_URL: "https://example.test/internal/paper-cycle" },
      async () => {
        fetches += 1;
        return { ok: true, status: 200 };
      },
    ),
    { message: "scheduler configuration missing" },
  );
  assert.equal(fetches, 0);
});


test("invokePaperCycle reports only HTTP status for provider failure", async () => {
  const token = "scheduler-secret";
  const responseBody = "postgresql://user:password@example.invalid/private";

  await assert.rejects(
    invokePaperCycle(
      {
        TARGET_URL: "https://example.test/internal/paper-cycle",
        SCHEDULER_TOKEN: token,
      },
      async () => ({
        ok: false,
        status: 503,
        text: async () => responseBody,
      }),
    ),
    (error) => {
      assert.equal(error.message, "paper cycle failed with HTTP 503");
      assert.equal(error.message.includes(token), false);
      assert.equal(error.message.includes(responseBody), false);
      return true;
    },
  );
});


test("scheduled handler passes the invocation promise to waitUntil", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  let scheduledPromise;
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200 };
  };

  try {
    worker.scheduled(
      {},
      {
        TARGET_URL: "https://example.test/internal/paper-cycle",
        SCHEDULER_TOKEN: "scheduler-secret",
      },
      {
        waitUntil(promise) {
          scheduledPromise = promise;
        },
      },
    );
    assert.ok(scheduledPromise instanceof Promise);
    await scheduledPromise;
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://example.test/internal/paper-cycle");
});
