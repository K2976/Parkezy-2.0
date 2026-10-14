import { useQuery } from '@tanstack/react-query';
import { Stack, useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { errorMessage } from '@/api/client';
import { legalApi } from '@/api/endpoints';
import type { LegalDocKind } from '@/api/types';
import { Card, ErrorState, Loading, Screen, Text } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

const TITLES: Record<LegalDocKind, string> = { terms: 'Terms of Service', privacy: 'Privacy Policy' };

/** Terms / Privacy rendered from the server, so the text always matches the live fees and rules.
 *  Lives outside the signed-in group: sign-up links here too. */
export default function LegalDocumentScreen() {
  const { doc: param } = useLocalSearchParams<{ doc: string }>();
  const doc: LegalDocKind = param === 'privacy' ? 'privacy' : 'terms';
  const { colors } = useTheme();
  const query = useQuery({ queryKey: ['legal', doc], queryFn: () => legalApi.get(doc), staleTime: 60 * 60 * 1000 });

  return (
    <>
      <Stack.Screen options={{ title: TITLES[doc] }} />
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : (
        <Screen>
          <Text variant="title">{query.data.title}</Text>
          <Text variant="small" style={{ marginBottom: spacing.md }}>
            Version {query.data.version} · Effective {query.data.effective_date}
          </Text>
          <Card>
            <Text>{query.data.summary}</Text>
          </Card>
          {query.data.sections.map((section) => (
            <View key={section.heading} style={{ marginTop: spacing.xl, gap: spacing.sm }}>
              <Text variant="heading" accessibilityRole="header">
                {section.heading}
              </Text>
              {section.blocks.map((block, i) =>
                block.type === 'list' ? (
                  <View key={i} style={{ gap: spacing.xs }}>
                    {block.items.map((item) => (
                      <View key={item} style={{ flexDirection: 'row', gap: spacing.sm }}>
                        <Text style={{ color: colors.accent, fontFamily: fonts.bodyBold }}>•</Text>
                        <Text style={{ flex: 1 }}>{item}</Text>
                      </View>
                    ))}
                  </View>
                ) : (
                  <Text key={i}>{block.text}</Text>
                ),
              )}
            </View>
          ))}
        </Screen>
      )}
    </>
  );
}
