import { useMutation } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Linking, Platform, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { supportApi } from '@/api/endpoints';
import type { SupportCategory } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { env } from '@/config/env';
import { Banner, Button, Card, Chip, IconOrb, Row, Screen, Section, Text, TextField } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

const CATEGORIES: { value: SupportCategory; label: string }[] = [
  { value: 'booking', label: 'A booking' },
  { value: 'payment', label: 'Payment or refund' },
  { value: 'account', label: 'My account' },
  { value: 'hosting', label: 'Hosting' },
  { value: 'privacy', label: 'Privacy & data' },
  { value: 'bug', label: 'Something’s broken' },
  { value: 'other', label: 'Other' },
];

/** Contact support. Outside the signed-in group on purpose: people locked out need it most. */
export default function ContactSupport() {
  const params = useLocalSearchParams<{ bookingId?: string; category?: SupportCategory }>();
  const { user } = useAuth();
  const { colors } = useTheme();
  const [category, setCategory] = useState<SupportCategory>(
    params.category ?? (params.bookingId ? 'booking' : 'account'),
  );
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');

  const send = useMutation({
    mutationFn: () =>
      supportApi.create({
        category,
        subject: subject.trim(),
        message: message.trim(),
        booking_id: user ? (params.bookingId ?? null) : null,
        email: user ? null : email.trim(),
        name: user ? null : name.trim() || null,
      }),
  });
  const fieldErrors = send.error instanceof ApiError ? send.error.fieldErrors : {};
  const ready = subject.trim().length >= 3 && message.trim().length >= 10 && (!!user || /\S+@\S+\.\S+/.test(email));

  if (send.data) {
    return (
      <Screen>
        <Stack.Screen options={{ title: 'Contact support' }} />
        <Card tier="strong">
          <View style={{ alignItems: 'center', gap: spacing.md, paddingVertical: spacing.lg }}>
            <IconOrb icon="checkmark" tone="success" size={64} />
            <Text variant="title" style={{ textAlign: 'center' }}>
              Message sent
            </Text>
            <Text style={{ textAlign: 'center' }}>
              Your reference is{' '}
              <Text style={{ fontFamily: fonts.bodyBold, color: colors.accent }}>#{send.data.reference}</Text>. We’ve
              emailed you a copy and usually reply within 1 business day.
            </Text>
          </View>
        </Card>
        <View style={{ marginTop: spacing.lg }}>
          <Button title="Done" onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} />
        </View>
      </Screen>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Stack.Screen options={{ title: 'Contact support' }} />
      <Screen>
        <Text variant="muted" style={{ marginBottom: spacing.md }}>
          Tell us what’s going on and we’ll get back to you by email
          {user ? ` at ${user.email}` : ''}.
        </Text>
        {send.error ? <Banner tone="danger">{errorMessage(send.error)}</Banner> : null}
        {params.bookingId && user ? (
          <Banner tone="info">This message will be linked to your booking so we can look it up.</Banner>
        ) : null}

        <Section title="What do you need help with?">
          <Row gap={0} style={{ flexWrap: 'wrap', marginHorizontal: -3 }}>
            {CATEGORIES.map((c) => (
              <Chip key={c.value} label={c.label} selected={category === c.value} onPress={() => setCategory(c.value)} />
            ))}
          </Row>
        </Section>

        {!user ? (
          <>
            <TextField
              label="Your email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              error={fieldErrors.email}
            />
            <TextField label="Your name (optional)" value={name} onChangeText={setName} autoComplete="name" />
          </>
        ) : null}
        <TextField
          label="Subject"
          value={subject}
          onChangeText={setSubject}
          maxLength={160}
          placeholder="e.g. Gate was locked when I arrived"
          error={fieldErrors.subject}
        />
        <TextField
          label="Message"
          value={message}
          onChangeText={setMessage}
          multiline
          maxLength={5000}
          style={{ minHeight: 140, textAlignVertical: 'top' }}
          hint="Include dates, the parking spot and anything you’ve already tried"
          error={fieldErrors.message}
        />
        <Button title="Send message" onPress={() => send.mutate()} loading={send.isPending} disabled={!ready} />

        <Text variant="small" style={{ textAlign: 'center', marginTop: spacing.xl }}>
          Prefer email? Write to{' '}
          <Text
            variant="small"
            style={{ fontFamily: fonts.bodyBold, color: colors.accent }}
            onPress={() => Linking.openURL(`mailto:${env.supportEmail}`)}>
            {env.supportEmail}
          </Text>
        </Text>
      </Screen>
    </KeyboardAvoidingView>
  );
}
