import { createApp } from "./app.ts";
import { assertRuntimeConfig } from "./config.ts";
import { adaptDatabase } from "./db.ts";
import { assertMailerAllowed, mailerFromEnv } from "./mailer.ts";
import { limiterFromBinding } from "./rate-limit.ts";

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    assertMailerAllowed(env);
    assertRuntimeConfig(env);
    const app = createApp({
      db: adaptDatabase(env.DB),
      mailer: mailerFromEnv(env),
      ipLimiter: limiterFromBinding(env.IP_RATE_LIMITER),
      env,
      waitUntil: (promise) => {
        ctx.waitUntil(promise);
      },
    });
    return app.fetch(request);
  },
} satisfies ExportedHandler<Env>;
