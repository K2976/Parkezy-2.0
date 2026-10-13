import { router } from 'expo-router';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { Banner, Button, Screen, Text, TextField } from '@/ui/components';
import { spacing } from '@/ui/theme';

/** Two steps on one screen: request a code by email, then set a new password with it. */
export default function ForgotPassword() {
  const [step, setStep] = useState<'email' | 'reset'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<{ tone: 'danger' | 'success'; text: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setMessage(null);
    setErrors({});
    setLoading(true);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fieldErrors);
        setMessage({ tone: 'danger', text: e.message });
      } else setMessage({ tone: 'danger', text: 'Something went wrong' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <Text variant="display" accessibilityRole="header" style={{ marginBottom: spacing.sm }}>
        Reset password
      </Text>
      <Text variant="muted" style={{ marginBottom: spacing.lg }}>
        {step === 'email'
          ? 'We’ll email you a code to choose a new password.'
          : `Enter the code we sent to ${email} and your new password.`}
      </Text>
      {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}
      {step === 'email' ? (
        <>
          <TextField label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" error={errors.email} />
          <Button
            title="Send code"
            loading={loading}
            disabled={!email}
            onPress={() =>
              run(async () => {
                await authApi.forgotPassword(email.trim());
                setStep('reset');
              })
            }
          />
        </>
      ) : (
        <>
          <TextField label="Code" value={code} onChangeText={setCode} keyboardType="number-pad" autoComplete="one-time-code" maxLength={10} error={errors.code} />
          <TextField
            label="New password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="new-password"
            hint="At least 8 characters with letters and numbers"
            error={errors.new_password}
          />
          <Button
            title="Update password"
            loading={loading}
            disabled={!code || password.length < 8}
            onPress={() =>
              run(async () => {
                await authApi.resetPassword({ email: email.trim(), code, new_password: password });
                router.replace('/sign-in');
              })
            }
          />
          <Button title="Send a new code" kind="ghost" onPress={() => run(() => authApi.forgotPassword(email.trim()).then(() => undefined))} />
        </>
      )}
    </Screen>
  );
}
