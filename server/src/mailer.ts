export interface LoginEmail {
  to: string;
  loginUrl: string;
}

export interface LoginMailer {
  sendLoginEmail(message: LoginEmail): Promise<void>;
}

/**
 * Records messages in memory. This is the only mailer in this slice.
 * mailerFromEnv refuses to return it when ENVIRONMENT is production.
 */
export class RecordingMailer implements LoginMailer {
  readonly sent: LoginEmail[] = [];

  sendLoginEmail(message: LoginEmail): Promise<void> {
    this.sent.push({ to: message.to, loginUrl: message.loginUrl });
    return Promise.resolve();
  }
}

export function assertMailerAllowed(
  env: { ENVIRONMENT: string; MAILER: string },
  mailer?: LoginMailer,
): void {
  const recordingBinding = env.MAILER === "recording" || mailer instanceof RecordingMailer;
  if (env.ENVIRONMENT === "production" && recordingBinding) {
    throw new Error("The recording mailer cannot be the production binding");
  }
}

export function mailerFromEnv(env: { ENVIRONMENT: string; MAILER: string }): LoginMailer {
  assertMailerAllowed(env);
  if (env.ENVIRONMENT !== "production" && env.MAILER === "recording") {
    return new RecordingMailer();
  }
  throw new Error("No mailer is configured");
}
