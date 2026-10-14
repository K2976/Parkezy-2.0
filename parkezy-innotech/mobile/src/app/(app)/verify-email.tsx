import { Redirect, router } from 'expo-router';
import { useState } from 'react';

import { errorMessage } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { Banner, Button, Screen, Text, TextField } from '@/ui/components';
import { spacing } from '@/ui/theme';

export default function VerifyEmail() {
  const { user, setUser } = useAuth();
  const [code, setCode] = useState('');
  const [message, setMessage] = useState<{ tone: 'danger' | 'success'; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const verify = async () => {
    setLoading(true);
    setMessage(null);
    try {
      setUser(await authApi.verifyEmail(code.trim()));
      if (router.canGoBack()) router.back();
      else router.replace('/');
    } catch (e) {
      setMessage({ tone: 'danger', text: errorMessage(e) });
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    setMessage(null);
    try {
      const { message: text } = await authApi.resendVerification();
      setMessage({ tone: 'success', text });
    } catch (e) {
      setMessage({ tone: 'danger', text: errorMessage(e) });
    }
  };

  // Already verified (e.g. opened from an old link): nothing to do here.
  if (user?.email_verified && !message) return <Redirect href="/" />;

  return (
    <Screen>
      <Text variant="heading" style={{ marginBottom: spacing.sm }}>
        Check your inbox
      </Text>
      <Text variant="muted" style={{ marginBottom: spacing.lg }}>
        We sent a code to {user?.email}. Enter it to start booking and hosting.
      </Text>
      {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}
      <TextField label="Verification code" value={code} onChangeText={setCode} keyboardType="number-pad" autoComplete="one-time-code" maxLength={10} />
      <Button title="Verify" onPress={verify} loading={loading} disabled={code.trim().length < 4} />
      <Button title="Send a new code" kind="ghost" onPress={resend} style={{ marginTop: spacing.sm }} />
    </Screen>
  );
}
