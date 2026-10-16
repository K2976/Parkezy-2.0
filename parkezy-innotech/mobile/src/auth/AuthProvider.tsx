import { useClerk, useSSO } from '@clerk/expo';
import { useQueryClient } from '@tanstack/react-query';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { api, ApiError, NETWORK_ERROR } from '@/api/client';
import { authApi, meApi } from '@/api/endpoints';
import type { AuthResponse, Tokens, User } from '@/api/types';
import { tokenStore } from '@/auth/tokenStore';
import { unregisterPushToken } from '@/services/push';

type Status = 'loading' | 'signedOut' | 'signedIn';

type AuthContextValue = {
  status: Status;
  user: User | null;
  signIn: (email: string, password: string) => Promise<User>;
  signInWithGoogle: () => Promise<User>;
  signUp: (input: { email: string; password: string; full_name: string; phone?: string | null }) => Promise<User>;
  signOut: () => Promise<void>;
  setUser: (user: User) => void;
  reloadUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUser] = useState<User | null>(null);
  const access = useRef<string | null>(null);
  const refresh = useRef<string | null>(null);

  const storeTokens = useCallback(async (tokens: Tokens) => {
    access.current = tokens.access_token;
    refresh.current = tokens.refresh_token;
    await tokenStore.saveRefresh(tokens.refresh_token);
  }, []);

  const clearSession = useCallback(async () => {
    access.current = null;
    refresh.current = null;
    await tokenStore.clear();
    // Never leak one account's cached data into the next session.
    queryClient.clear();
    setUser(null);
    setStatus('signedOut');
  }, [queryClient]);

  // The API client asks the auth layer for tokens through this narrow interface.
  useEffect(() => {
    api.attach({
      accessToken: () => access.current,
      refresh: async () => {
        if (!refresh.current) return null;
        try {
          const tokens = await authApi.refresh(refresh.current);
          await storeTokens(tokens);
          return tokens.access_token;
        } catch (error) {
          // Offline is not a lost session: surface the network error instead of signing out.
          if (error instanceof ApiError && error.code === NETWORK_ERROR) throw error;
          return null;
        }
      },
      onSessionLost: () => {
        void clearSession();
      },
    });
    return () => api.attach(null);
  }, [clearSession, storeTokens]);

  // Restore the session on launch.
  useEffect(() => {
    (async () => {
      const saved = await tokenStore.loadRefresh();
      if (!saved) {
        setStatus('signedOut');
        return;
      }
      try {
        await storeTokens(await authApi.refresh(saved));
        setUser(await meApi.get());
        setStatus('signedIn');
      } catch (error) {
        if (error instanceof ApiError && error.code === NETWORK_ERROR) {
          // Offline at launch: keep the refresh token and let the user retry.
          refresh.current = saved;
          setStatus('signedOut');
          return;
        }
        await clearSession();
      }
    })();
  }, [clearSession, storeTokens]);

  const { startSSOFlow } = useSSO();
  const clerk = useClerk();

  const accept = useCallback(
    async (response: AuthResponse) => {
      queryClient.clear();
      await storeTokens(response.tokens);
      setUser(response.user);
      setStatus('signedIn');
      return response.user;
    },
    [queryClient, storeTokens],
  );

  const signInWithGoogle = useCallback(async (): Promise<User> => {
    const ssoResult = await startSSOFlow({
      strategy: 'oauth_google',
    });

    const sessionId =
      ssoResult.createdSessionId ||
      ssoResult.signIn?.createdSessionId ||
      ssoResult.signUp?.createdSessionId;

    if (!sessionId) {
      const type = (ssoResult as any).authSessionResult?.type;
      if (type === 'cancel' || type === 'dismiss') {
        throw new Error('Google sign-in popup was closed or cancelled.');
      }
      throw new Error(`Google sign-in could not be completed (${type || 'no session created'}).`);
    }

    if (ssoResult.setActive) {
      await ssoResult.setActive({ session: sessionId });
    }

    // Retrieve the Clerk session JWT
    let idToken: string | null = null;
    if (clerk.session) {
      idToken = await clerk.session.getToken();
    }
    if (!idToken && clerk.client?.sessions) {
      const activeSession = clerk.client.sessions.find((s) => s.id === sessionId);
      idToken = (await activeSession?.getToken()) ?? null;
    }

    if (!idToken) {
      throw new Error('Could not retrieve authentication token from Clerk session.');
    }

    const email =
      ssoResult.signUp?.emailAddress ||
      ssoResult.signIn?.identifier ||
      clerk.user?.primaryEmailAddress?.emailAddress ||
      clerk.session?.user?.primaryEmailAddress?.emailAddress ||
      undefined;

    const fullName =
      (ssoResult.signUp?.firstName
        ? `${ssoResult.signUp.firstName} ${ssoResult.signUp.lastName || ''}`.trim()
        : undefined) ||
      clerk.user?.fullName ||
      clerk.session?.user?.fullName ||
      undefined;

    const authRes = await authApi.social({
      provider: 'clerk',
      id_token: idToken,
      full_name: fullName,
      email: email,
    });
    return accept(authRes);
  }, [startSSOFlow, clerk, accept]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      signIn: async (email, password) => accept(await authApi.login({ email, password })),
      signInWithGoogle,
      signUp: async (input) => accept(await authApi.register(input)),
      signOut: async () => {
        await unregisterPushToken().catch(() => undefined);
        if (refresh.current) await authApi.logout(refresh.current).catch(() => undefined);
        await clerk.signOut().catch(() => undefined);
        await clearSession();
      },
      setUser,
      reloadUser: async () => setUser(await meApi.get()),
    }),
    [status, user, accept, signInWithGoogle, clerk, clearSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

/** For screens that only render when signed in. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error('useUser used while signed out');
  return user;
}
