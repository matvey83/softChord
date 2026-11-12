export interface LoginEmail {
  to: string;
  loginUrl: string;
}

export interface LoginMailer {
  sendLoginEmail(message: LoginEmail): Promise<void>;
}

/**
 * Records messages in memory. This is the only mailer in this slice.
 * mailerFromEnv returns it only when ENVIRONMENT is development, dev, or test.
 */
export class RecordingMailer implements LoginMailer {
  readonly sent: LoginEmail[] = [];

  sendLoginEmail(message: LoginEmail): Promise<void> {
    this.sent.push({ to: message.to, loginUrl: message.loginUrl });
    return Promise.resolve();
  }
}

export function recordingEnvironment(environment: string): boolean {
  return environment === "development" || environment === "dev" || environment === "test";
}

export function assertMailerAllowed(
  env: { ENVIRONMENT: string; MAILER: string },
  mailer?: LoginMailer,
): void {
  const recordingBinding = env.MAILER === "recording" || mailer instanceof RecordingMailer;
  if (recordingBinding && !recordingEnvironment(env.ENVIRONMENT)) {
    throw new Error("The recording mailer can only be used when ENVIRONMENT is dev or test");
  }
}

export function mailerFromEnv(env: { ENVIRONMENT: string; MAILER: string }): LoginMailer {
  assertMailerAllowed(env);
  if (recordingEnvironment(env.ENVIRONMENT) && env.MAILER === "recording") {
    return new RecordingMailer();
  }
  throw new Error("No mailer is configured");
}
