import type { ReactNode } from 'react';
import { View } from 'react-native';

import { Text } from '@/ui/components';
import { spacing } from '@/ui/theme';

/** Large Nunito page title used by the tab screens (they have no native header). */
export function ScreenTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: spacing.lg, gap: spacing.md }}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text variant="display" accessibilityRole="header">
          {title}
        </Text>
        {subtitle ? <Text variant="muted">{subtitle}</Text> : null}
      </View>
      {right}
    </View>
  );
}
