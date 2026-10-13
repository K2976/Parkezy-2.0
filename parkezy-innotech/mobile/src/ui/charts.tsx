import { View } from 'react-native';
import Svg, { Circle, Rect } from 'react-native-svg';

import { Text } from '@/ui/components';
import { radius, spacing, useTheme } from '@/ui/theme';

/** Daily bars from real data. Solid fills only (no gradients); today's bar is emphasised. */
export function BarChart({
  values,
  labels,
  height = 96,
  inverse,
  accessibilityLabel,
}: {
  values: number[];
  labels?: string[];
  height?: number;
  inverse?: boolean;
  accessibilityLabel: string;
}) {
  const { colors } = useTheme();
  const allZero = values.every((v) => v === 0);
  const max = Math.max(...values, 1);
  const n = Math.max(values.length, 1);
  const gap = 6;
  const barColor = inverse ? colors.onFeaturedMuted : colors.accentSoft;
  const lastColor = inverse ? colors.onFeatured : colors.accent;
  return (
    <View accessible accessibilityLabel={accessibilityLabel} style={{ position: 'relative' }}>
      <Svg width="100%" height={height} viewBox={`0 0 ${n * 20} ${height}`} preserveAspectRatio="none">
        {values.map((v, i) => {
          const h = allZero ? 8 : Math.max((v / max) * (height - 4), v > 0 ? 6 : 3);
          return (
            <Rect
              key={i}
              x={i * 20 + gap / 2}
              y={height - h}
              width={20 - gap}
              height={h}
              rx={4}
              fill={allZero ? barColor : i === values.length - 1 ? lastColor : barColor}
              opacity={allZero ? 0.25 : v > 0 ? 1 : 0.5}
            />
          );
        })}
      </Svg>
      {allZero ? (
        <View
          style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 20, alignItems: 'center', justifyContent: 'center' }}
          pointerEvents="none">
          <Text variant="small" style={inverse ? { color: colors.onFeaturedMuted } : undefined}>
            No completed bookings in this period yet
          </Text>
        </View>
      ) : null}
      {labels ? (
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.xs }}>
          <Text variant="small" style={inverse ? { color: colors.onFeaturedMuted } : undefined}>
            {labels[0]}
          </Text>
          <Text variant="small" style={inverse ? { color: colors.onFeaturedMuted } : undefined}>
            {labels[labels.length - 1]}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

/** Progress ring, e.g. parking time used. `progress` is 0..1. */
export function ProgressRing({
  progress,
  size = 132,
  stroke = 12,
  center,
  accessibilityLabel,
  tone = 'accent',
}: {
  progress: number;
  size?: number;
  stroke?: number;
  center: React.ReactNode;
  accessibilityLabel: string;
  tone?: 'accent' | 'warning';
}) {
  const { colors, shadows } = useTheme();
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.min(Math.max(progress, 0), 1);
  return (
    <View
      accessible
      accessibilityLabel={accessibilityLabel}
      style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.clay, boxShadow: shadows.clayRaised }}>
      <Svg width={size} height={size}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={colors.clayRecessed} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={tone === 'warning' ? colors.warning : colors.accent}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={circumference * (1 - clamped)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center' }}>{center}</View>
    </View>
  );
}

/** Recessed clay meter for a ratio, e.g. free slots out of total. */
export function Meter({ value, total, accessibilityLabel }: { value: number; total: number; accessibilityLabel: string }) {
  const { colors, shadows } = useTheme();
  const ratio = total > 0 ? Math.min(value / total, 1) : 0;
  return (
    <View
      accessible
      accessibilityLabel={accessibilityLabel}
      style={{ height: 10, borderRadius: radius.pill, backgroundColor: colors.clayRecessed, boxShadow: shadows.clayPressed, overflow: 'hidden' }}>
      <View
        style={{
          width: `${ratio * 100}%`,
          height: '100%',
          borderRadius: radius.pill,
          backgroundColor: ratio === 0 ? colors.muted : ratio < 0.25 ? colors.warning : colors.success,
        }}
      />
    </View>
  );
}
