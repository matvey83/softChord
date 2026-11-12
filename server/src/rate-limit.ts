export interface IpRateLimiter {
  /** True when this IP may continue. False means do not send. */
  allow(ip: string): Promise<boolean>;
}

export interface RateLimitBinding {
  limit(options: { key: string }): Promise<{ success: boolean }>;
}

/** Adapts the Workers Rate Limiting binding. Failures fail closed (no send). */
export function limiterFromBinding(binding: RateLimitBinding): IpRateLimiter {
  return {
    async allow(ip: string): Promise<boolean> {
      try {
        const result = await binding.limit({ key: `ip:${ip}` });
        return result.success;
      } catch {
        console.error(JSON.stringify({ event: "ip_rate_limit_failed" }));
        return false;
      }
    },
  };
}

export function allowAllLimiter(): IpRateLimiter {
  return {
    allow(): Promise<boolean> {
      return Promise.resolve(true);
    },
  };
}

export function clientIp(request: Request): string {
  const header = request.headers.get("cf-connecting-ip");
  if (header && header.length <= 64 && /^[0-9a-fA-F:.]+$/.test(header)) return header;
  return "unknown";
}
