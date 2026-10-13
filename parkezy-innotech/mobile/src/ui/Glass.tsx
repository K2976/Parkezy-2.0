import { BlurView } from 'expo-blur';
import type { ReactNode } from 'react';
import { type StyleProp, StyleSheet, View, type ViewStyle } from 'react-native';

import { useBlurTarget } from '@/ui/Backdrop';
import { type GlassTier, glassTiers, radius, useTheme } from '@/ui/theme';

/**
 * Frosted glass surface — the four-part formula:
 *   translucent fill (tier) + backdrop blur + light 1px border + top-edge inner highlight,
 * plus a soft 10% shadow. Content sits on top, unblurred, so text stays crisp.
 * Glass is for SURFACES only; interactive controls are clay (see components.tsx).
 */
export function Glass({
  tier = 'mid',
  children,
  style,
  contentStyle,
  rounded = radius.card,
}: {
  tier?: GlassTier;
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
  contentStyle?: StyleProp<ViewStyle>;
  rounded?: number;
}) {
  const { colors, shadows, scheme } = useTheme();
  const target = useBlurTarget();
  const spec = glassTiers[tier];
  return (
    <View style={[{ borderRadius: rounded, boxShadow: shadows.glass, overflow: 'hidden' }, style]}>
      <View style={[StyleSheet.absoluteFill, { borderRadius: rounded, overflow: 'hidden' }]} pointerEvents="none">
        <BlurView
          intensity={spec.blur}
          tint={scheme === 'dark' ? 'dark' : 'light'}
          blurTarget={target ?? undefined}
          blurMethod={target ? 'dimezisBlurViewSdk31Plus' : 'none'}
          style={StyleSheet.absoluteFill}
        />
        <View style={[StyleSheet.absoluteFill, { backgroundColor: colors[spec.fill] }]} />
        {/* Glass mirror top specular beam catching light across the beveled pane */}
        <View
          style={{
            position: 'absolute',
            top: 0,
            left: rounded / 4,
            right: rounded / 4,
            height: 1.5,
            backgroundColor: colors.glassHighlight,
            opacity: 0.95,
          }}
        />
      </View>
      <View
        style={[
          {
            borderRadius: rounded,
            borderWidth: 1.2,
            borderColor: colors.glassBorder,
            borderTopColor: colors.glassHighlight,
            overflow: 'hidden',
          },
          contentStyle,
        ]}>
        {children}
      </View>
    </View>
  );
}
