/** Booking windows must sit on the server's step boundary (GET /v1/config booking_step_minutes). */
export function roundUpToStep(date: Date, stepMinutes: number): Date {
  const ms = stepMinutes * 60_000;
  return new Date(Math.ceil(date.getTime() / ms) * ms);
}

/** "Park now": the current step block is still bookable on the server. */
export function currentStepStart(date: Date, stepMinutes: number): Date {
  const ms = stepMinutes * 60_000;
  return new Date(Math.floor(date.getTime() / ms) * ms);
}

export function addMinutes(date: Date, minutes: number): Date {
  return new Date(date.getTime() + minutes * 60_000);
}

export function minutesBetween(a: Date, b: Date): number {
  return Math.round((b.getTime() - a.getTime()) / 60_000);
}

export function durationOptions(min: number, max: number, step: number): number[] {
  const presets = [30, 60, 90, 120, 180, 240, 360, 480, 720, 1440];
  return presets.filter((m) => m >= min && m <= max && m % step === 0);
}
