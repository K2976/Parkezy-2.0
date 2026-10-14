import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { meApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { Banner, Button, Card, IconOrb, Screen, Text, TextField } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

const CONSEQUENCES = [
  'Your name, email and phone number are erased and you can’t sign in again.',
  'You’re signed out on every device and stop receiving notifications.',
  'Any parking spaces you host are unpublished.',
  'Booking and payment records the law requires us to keep are anonymised.',
];

/** In-page confirmation (not Alert.alert, which is a no-op on web) plus the password again,
 *  so a borrowed unlocked phone can't wipe the account. */
export default function DeleteAccount() {
  const { user, signOut } = useAuth();
  const { colors } = useTheme();
  const [password, setPassword] = useState('');
  const [deleted, setDeleted] = useState(false);

  const remove = useMutation({
    mutationFn: () => meApi.delete(password),
    onSuccess: () => setDeleted(true),
  });
  const code = remove.error instanceof ApiError ? remove.error.code : null;

  if (deleted) {
    return (
      <Screen>
        <Card tier="strong">
          <View style={{ alignItems: 'center', gap: spacing.md, paddingVertical: spacing.lg }}>
            <IconOrb icon="checkmark" tone="success" size={64} />
            <Text variant="title" style={{ textAlign: 'center' }}>
              Account deleted
            </Text>
            <Text style={{ textAlign: 'center' }}>
              We’ve emailed a confirmation to {user?.email}. Thanks for parking with us.
            </Text>
          </View>
        </Card>
        <View style={{ marginTop: spacing.lg }}>
          {/* The server already revoked every session; this clears the local one and returns to sign-in. */}
          <Button title="Close" onPress={() => signOut()} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={{ alignItems: 'center', marginBottom: spacing.lg }}>
        <IconOrb icon="trash-outline" tone="danger" size={64} />
      </View>
      <Text variant="title" style={{ textAlign: 'center', marginBottom: spacing.md }}>
        Delete your account?
      </Text>
      <Card>
        {CONSEQUENCES.map((line) => (
          <View key={line} style={{ flexDirection: 'row', gap: spacing.sm }}>
            <Text style={{ color: colors.danger, fontFamily: fonts.bodyBold }}>•</Text>
            <Text style={{ flex: 1 }}>{line}</Text>
          </View>
        ))}
        <Text variant="small" style={{ marginTop: spacing.sm }}>
          This can’t be undone. You can register again later with the same email.{' '}
          <Text
            variant="small"
            style={{ fontFamily: fonts.bodyBold, color: colors.accent }}
            onPress={() => router.push({ pathname: '/legal/[doc]', params: { doc: 'privacy' } })}>
            How we handle deletion
          </Text>
        </Text>
      </Card>

      <View style={{ marginTop: spacing.lg }}>
        {code === 'active_bookings' ? (
          <Banner tone="warning">
            <Text>
              {errorMessage(remove.error)}.{' '}
              <Text
                style={{ fontFamily: fonts.bodyBold, color: colors.accent }}
                onPress={() => router.push('/bookings')}>
                View bookings
              </Text>
            </Text>
          </Banner>
        ) : remove.error ? (
          <Banner tone="danger">{errorMessage(remove.error)}</Banner>
        ) : null}
        <TextField
          label="Enter your password to confirm"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="current-password"
          onSubmitEditing={() => password && remove.mutate()}
        />
        <Button
          title="Permanently delete account"
          kind="danger"
          onPress={() => remove.mutate()}
          loading={remove.isPending}
          disabled={!password}
        />
        <View style={{ marginTop: spacing.sm }}>
          <Button title="Keep my account" kind="secondary" onPress={() => router.back()} />
        </View>
      </View>
    </Screen>
  );
}
