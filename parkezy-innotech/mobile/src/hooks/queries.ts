import { useQuery } from '@tanstack/react-query';

import { discoveryApi } from '@/api/endpoints';

export const keys = {
  config: ['config'] as const,
  search: (params: object) => ['listings', 'search', params] as const,
  listing: (id: string, window?: object) => ['listings', id, window ?? null] as const,
  myBookings: (group?: string) => ['bookings', 'mine', group ?? 'all'] as const,
  booking: (id: string) => ['bookings', id] as const,
  access: (id: string) => ['bookings', id, 'access'] as const,
  hostDashboard: ['host', 'dashboard'] as const,
  hostListings: ['host', 'listings'] as const,
  hostListing: (id: string) => ['host', 'listings', id] as const,
  hostBookings: (group?: string) => ['host', 'bookings', group ?? 'all'] as const,
  notifications: ['notifications'] as const,
  disputes: ['disputes'] as const,
};

/** Business rules from the server; every screen that needs a limit or rate reads them here. */
export function useConfig() {
  return useQuery({ queryKey: keys.config, queryFn: discoveryApi.config, staleTime: 5 * 60_000 });
}
