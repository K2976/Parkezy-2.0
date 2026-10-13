import type { BookingStatus } from '@/api/types';

export function money(amount: string | number, currency: string): string {
  const value = typeof amount === 'string' ? Number(amount) : amount;
  try {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
}

/** Times are shown in the listing's timezone, which is where the driver will physically be. */
export function dateTime(iso: string, timeZone?: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    timeZone,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function time(iso: string, timeZone?: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', { timeZone, hour: 'numeric', minute: '2-digit' });
}

export function duration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export function distance(meters: number): string {
  return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
}

export function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export const STATUS_LABEL: Record<BookingStatus, string> = {
  pending_approval: 'Waiting for host',
  pending_payment: 'Payment needed',
  confirmed: 'Confirmed',
  checked_in: 'Parked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  rejected: 'Declined',
  expired: 'Expired',
};

export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
