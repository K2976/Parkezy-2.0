import { Text as RNText, View } from 'react-native';

import { Squishable } from '@/ui/components';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';

/** Clay segmented control: a recessed tray; the selected segment is a raised clay key. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { key: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  const { colors, shadows } = useTheme();
  return (
    <View
      accessibilityRole="tablist"
      style={{ flexDirection: 'row', padding: 5, gap: 4, borderRadius: radius.control + 4, backgroundColor: colors.clayRecessed, boxShadow: shadows.clayPressed }}>
      {options.map((o) => {
        const selected = o.key === value;
        return (
          <Squishable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={o.label}
            onPress={() => onChange(o.key)}
            style={{ flex: 1 }}>
            <View
              style={{
                minHeight: 40,
                borderRadius: radius.control,
                alignItems: 'center',
                justifyContent: 'center',
                paddingHorizontal: spacing.sm,
                backgroundColor: selected ? colors.clay : 'transparent',
                boxShadow: selected ? shadows.clayRaised : undefined,
              }}>
              <RNText style={{ fontFamily: selected ? fonts.heading : fonts.bodyMedium, fontSize: 14, color: selected ? colors.accent : colors.muted }}>
                {o.label}
              </RNText>
            </View>
          </Squishable>
        );
      })}
    </View>
  );
}
