import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { env } from '@/config/env';
import { Banner, Button, Card, Screen, Text, TextField } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

export default function SignUp() {
  const { signUp } = useAuth();
  const { colors } = useTheme();
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  const submit = async () => {
    setError(null);
    setErrors({});
    setLoading(true);
    try {
      // On success the root navigator switches to the app, which prompts for email verification.
      await signUp({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        password: form.password,
      });
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fieldErrors);
        setError(e.message);
      } else setError('Could not create your account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Screen>
        <Text variant="display" accessibilityRole="header" style={{ marginBottom: spacing.lg }}>
          Create account
        </Text>
        <Card tier="strong">
        {error ? <Banner tone="danger">{error}</Banner> : null}
        {error ? <View style={{ height: spacing.md }} /> : null}
        <TextField label="Full name" value={form.full_name} onChangeText={set('full_name')} autoComplete="name" error={errors.full_name} />
        <TextField
          label="Email"
          value={form.email}
          onChangeText={set('email')}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
          error={errors.email}
        />
        <TextField
          label="Phone (optional)"
          value={form.phone}
          onChangeText={set('phone')}
          keyboardType="phone-pad"
          autoComplete="tel"
          placeholder="+91 98765 43210"
          hint="Needed later if you want to host a spot"
          error={errors.phone}
        />
        <TextField
          label="Password"
          value={form.password}
          onChangeText={set('password')}
          secureTextEntry
          autoComplete="new-password"
          hint="At least 8 characters with letters and numbers"
          error={errors.password}
        />
        <Button
          title="Create account"
          onPress={submit}
          loading={loading}
          disabled={!form.full_name || !form.email || form.password.length < 8}
        />
        </Card>
        <Text variant="small" style={{ marginTop: spacing.lg, textAlign: 'center' }}>
          By continuing you agree to our{' '}
          <Text variant="small" style={{ fontFamily: fonts.bodyBold, color: colors.accent }} onPress={() => WebBrowser.openBrowserAsync(env.termsUrl)}>
            Terms
          </Text>{' '}
          and{' '}
          <Text variant="small" style={{ fontFamily: fonts.bodyBold, color: colors.accent }} onPress={() => WebBrowser.openBrowserAsync(env.privacyUrl)}>
            Privacy Policy
          </Text>
          .
        </Text>
      </Screen>
    </KeyboardAvoidingView>
  );
}
