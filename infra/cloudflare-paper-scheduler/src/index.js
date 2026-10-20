export async function invokePaperCycle(env, fetchImpl = fetch) {
  if (!env.TARGET_URL || !env.SCHEDULER_TOKEN) {
    throw new Error("scheduler configuration missing");
  }

  const response = await fetchImpl(env.TARGET_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.SCHEDULER_TOKEN}`,
      "User-Agent": "ai-trading-cloudflare-scheduler/1",
      "X-Scheduler-Source": "cloudflare",
    },
  });

  if (!response.ok) {
    throw new Error(`paper cycle failed with HTTP ${response.status}`);
  }

  // Reject legacy HTTP 200 responses that still report partial failures.
  const payload = await response.json().catch(() => null);
  if (!payload || payload.ok !== true) {
    throw new Error("paper cycle response not successful");
  }
}

export default {
  scheduled(_event, env, ctx) {
    ctx.waitUntil(invokePaperCycle(env));
  },
};
