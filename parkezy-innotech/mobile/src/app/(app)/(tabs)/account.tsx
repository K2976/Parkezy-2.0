import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { Alert, Linking, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { meApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { env } from '@/config/env';
import { Banner, Card, ListItem, Pill, Row, Screen, Section, Text } from '@/ui/components';
import { ScreenTitle } from '@/ui/ScreenTitle';
import { fonts, spacing, useTheme } from '@/ui/theme';

function initials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
}

export default function Account() {
  const { user, signOut } = useAuth();
  const { colors, shadows } = useTheme();
  const remove = useMutation({ mutationFn: meApi.delete, onSuccess: () => signOut() });

  const confirmDelete = () =>
    Alert.alert(
      'Delete your account?',
      'Your profile and personal details are removed permanently. You need to finish or cancel active bookings first.',
      [
        { text: 'Keep account', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => remove.mutate() },
      ],
    );

  return (
    <Screen edges={['top']}>
      <ScreenTitle title="Account" />
      <Card tier="strong">
        <Row gap={spacing.lg}>
          {/* Clay avatar orb with initials (no photo/emoji placeholder). */}
          <View
            style={{
              width: 64,
              height: 64,
              borderRadius: 32,
              backgroundColor: colors.accentSoft,
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: shadows.clayRaised,
            }}>
            <Text style={{ fontFamily: fonts.display, fontSize: 24, color: colors.accent }}>{initials(user?.full_name ?? '')}</Text>
          </View>
          <View style={{ flex: 1, gap: 4 }}>
            <Text variant="heading">{user?.full_name}</Text>
            <Text variant="muted" numberOfLines={1}>
              {user?.email}
            </Text>
            <Row gap={spacing.xs}>
              <Pill label={user?.email_verified ? 'Verified' : 'Not verified'} tone={user?.email_verified ? 'success' : 'warning'} />
              {user?.is_host ? <Pill label="Host" tone="accent" /> : null}
            </Row>
          </View>
        </Row>
      </Card>
      {!user?.email_verified ? (
        <View style={{ marginTop: spacing.md }}>
          <Banner tone="warning">
            <Text>
              Your email isn’t verified.{' '}
              <Text style={{ fontFamily: fonts.bodyBold, color: colors.accent }} onPress={() => router.push('/verify-email')}>
                Verify now
              </Text>
            </Text>
          </Banner>
        </View>
      ) : null}
      {remove.error ? (
        <View style={{ marginTop: spacing.md }}>
          <Banner tone="danger">{errorMessage(remove.error)}</Banner>
        </View>
      ) : null}

      <Section title="Account">
        <ListItem icon="notifications-outline" title="Notifications" onPress={() => router.push('/notifications')} />
        <ListItem icon="person-outline" title="Edit profile" onPress={() => router.push('/account/profile')} />
        <ListItem icon="key-outline" title="Change password" onPress={() => router.push('/account/password')} />
      </Section>

      <Section title="Help">
        <ListItem icon="mail-outline" title="Contact support" subtitle={env.supportEmail} onPress={() => Linking.openURL(`mailto:${env.supportEmail}`)} />
        <ListItem icon="document-text-outline" title="Terms of service" onPress={() => WebBrowser.openBrowserAsync(env.termsUrl)} />
        <ListItem icon="shield-checkmark-outline" title="Privacy policy" onPress={() => WebBrowser.openBrowserAsync(env.privacyUrl)} />
      </Section>

      <Section title="Session">
        <ListItem icon="log-out-outline" title="Sign out" onPress={() => signOut()} />
        <ListItem icon="trash-outline" title="Delete account" danger onPress={confirmDelete} />
      </Section>
    </Screen>
  );
}
