import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';

import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { Banner, Button, Card, IconOrb, Row, Screen, Text, TextField } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

export default function SignIn() {
  const { signIn } = useAuth();
  const { colors } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      await signIn(email.trim(), password);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not sign in');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Screen edges={['top', 'bottom']} contentStyle={{ flexGrow: 1, justifyContent: 'center', paddingBottom: spacing.xxl }}>
        <View style={{ alignItems: 'center', gap: spacing.sm, marginBottom: spacing.xl }}>
          <IconOrb icon="car-sport-outline" size={72} />
          <Text variant="display" accessibilityRole="header" style={{ textAlign: 'center', marginTop: spacing.xs }}>
            Parkezy
          </Text>
          <Text variant="muted" style={{ textAlign: 'center', maxWidth: 290 }}>
            Find a spot in seconds, or earn from the one you already have.
          </Text>
        </View>

        {/* Form panel is strong glass; everything you touch inside it is clay. */}
        <Card tier="strong">
          {error ? (
            <View style={{ marginBottom: spacing.md }}>
              <Banner tone="danger">{error}</Banner>
            </View>
          ) : null}
          <TextField
            label="Email"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            textContentType="emailAddress"
          />
          <TextField
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="current-password"
            textContentType="password"
            onSubmitEditing={submit}
          />
          <Button title="Sign in" icon="arrow-forward" onPress={submit} loading={loading} disabled={!email || !password} />
          <Button title="Forgot password?" kind="ghost" size="sm" onPress={() => router.push('/forgot-password')} />
        </Card>

        <Row style={{ justifyContent: 'center', marginTop: spacing.xl }} gap={spacing.xs}>
          <Text variant="muted">New here?</Text>
          <Text
            accessibilityRole="link"
            onPress={() => router.push('/sign-up')}
            style={{ fontFamily: fonts.bodyBold, color: colors.accent, paddingVertical: spacing.sm }}>
            Create an account
          </Text>
        </Row>
        <Row style={{ justifyContent: 'center' }} gap={spacing.xs}>
          <Text variant="muted">Trouble signing in?</Text>
          <Text
            accessibilityRole="link"
            onPress={() => router.push('/support')}
            style={{ fontFamily: fonts.bodyBold, color: colors.accent, paddingVertical: spacing.sm }}>
            Contact support
          </Text>
        </Row>
      </Screen>
    </KeyboardAvoidingView>
  );
}
