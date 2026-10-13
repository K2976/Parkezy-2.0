import { bookingApi } from '@/api/endpoints';
import type { PaymentOrder } from '@/api/types';

type RazorpayResult = { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string };
type RazorpayCheckout = { open(options: Record<string, unknown>): Promise<RazorpayResult> };

/** The Razorpay SDK is native: present in development/production builds, absent in Expo Go. */
function loadCheckout(): RazorpayCheckout | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('react-native-razorpay');
    return (mod?.default ?? mod) as RazorpayCheckout;
  } catch {
    return null;
  }
}

export class PaymentUnavailableError extends Error {}
export class PaymentCancelledError extends Error {}

/**
 * Opens Razorpay checkout for the amount the server says is due, then sends the signed
 * result back to the server, which verifies it before confirming the booking.
 */
export async function payForBooking(bookingId: string, appName: string, accentColor: string): Promise<void> {
  const checkout = loadCheckout();
  if (!checkout) {
    throw new PaymentUnavailableError('Online payment needs the full app build (not Expo Go).');
  }
  const order: PaymentOrder = await bookingApi.createPayment(bookingId);
  let result: RazorpayResult;
  try {
    result = await checkout.open({
      key: order.key_id,
      order_id: order.order_id,
      amount: order.amount_minor,
      currency: order.currency,
      name: appName,
      description: order.description,
      prefill: { email: order.prefill_email, contact: order.prefill_phone ?? undefined },
      theme: { color: accentColor },
    });
  } catch {
    throw new PaymentCancelledError('Payment was not completed');
  }
  await bookingApi.confirmPayment(bookingId, {
    order_id: result.razorpay_order_id,
    payment_id: result.razorpay_payment_id,
    signature: result.razorpay_signature,
  });
}
