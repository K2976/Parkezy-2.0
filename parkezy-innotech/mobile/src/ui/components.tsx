import Ionicons from '@expo/vector-icons/Ionicons';
import { type ComponentProps, type ReactNode, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  type PressableProps,
  RefreshControl,
  ScrollView,
  type StyleProp,
  StyleSheet,
  Text as RNText,
  type TextProps,
  TextInput,
  type TextInputProps,
  type TextStyle,
  View,
  type ViewStyle,
} from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withTiming } from 'react-native-reanimated';
import { type Edge, SafeAreaView } from 'react-native-safe-area-context';

import type { BookingStatus } from '@/api/types';
import { Backdrop } from '@/ui/Backdrop';
import { Glass } from '@/ui/Glass';
import { controlHeight, fonts, type GlassTier, motion, radius, spacing, useTheme } from '@/ui/theme';
import { STATUS_LABEL } from '@/utils/format';

export type IconName = ComponentProps<typeof Ionicons>['name'];
export type Tone = 'accent' | 'info' | 'success' | 'warning' | 'danger' | 'neutral';

export function useTone(tone: Tone) {
  const { colors: c } = useTheme();
  return {
    accent: { fg: c.accent, bg: c.accentSoft },
    info: { fg: c.info, bg: c.infoSoft },
    success: { fg: c.success, bg: c.successSoft },
    warning: { fg: c.warning, bg: c.warningSoft },
    danger: { fg: c.danger, bg: c.dangerSoft },
    neutral: { fg: c.muted, bg: c.clayRecessed },
  }[tone];
}

// =================================================================== typography
// Nunito (rounded, heavy) for headings and numbers; DM Sans for reading.
type Variant = 'display' | 'title' | 'heading' | 'number' | 'body' | 'muted' | 'small' | 'label';
const variants: Record<Variant, TextStyle> = {
  display: { fontFamily: fonts.display, fontSize: 34, lineHeight: 38, letterSpacing: -0.5 },
  title: { fontFamily: fonts.heading, fontSize: 26, lineHeight: 31, letterSpacing: -0.3 },
  heading: { fontFamily: fonts.heading, fontSize: 18, lineHeight: 24 },
  number: { fontFamily: fonts.display, fontSize: 28, lineHeight: 32, letterSpacing: -0.4 },
  body: { fontFamily: fonts.body, fontSize: 16, lineHeight: 24 },
  muted: { fontFamily: fonts.body, fontSize: 15, lineHeight: 22 },
  small: { fontFamily: fonts.bodyMedium, fontSize: 13, lineHeight: 18 },
  label: { fontFamily: fonts.heading, fontSize: 12, letterSpacing: 1, textTransform: 'uppercase' },
};

export function Text({ variant = 'body', style, ...props }: TextProps & { variant?: Variant }) {
  const { colors } = useTheme();
  const color = variant === 'muted' || variant === 'small' || variant === 'label' ? colors.muted : colors.text;
  return <RNText {...props} style={[{ color }, variants[variant], style]} />;
}

// =================================================================== layout
export function Screen({
  children,
  scroll = true,
  refreshing,
  onRefresh,
  edges = ['bottom'],
  contentStyle,
}: {
  children: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  edges?: Edge[];
  contentStyle?: StyleProp<ViewStyle>;
}) {
  return (
    <Backdrop>
      <SafeAreaView edges={edges} style={{ flex: 1 }}>
        {scroll ? (
          <ScrollView
            contentContainerStyle={[styles.content, contentStyle]}
            keyboardShouldPersistTaps="handled"
            refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} /> : undefined}>
            {children}
          </ScrollView>
        ) : (
          <View style={[{ flex: 1 }, contentStyle]}>{children}</View>
        )}
      </SafeAreaView>
    </Backdrop>
  );
}

// =================================================================== clay physics
/** Press feedback shared by every clay control: squish down, release back. */
export function Squishable({
  children,
  scaleTo = motion.pressScale,
  style,
  ...props
}: Omit<PressableProps, 'children' | 'style'> & {
  children: ReactNode | ((pressed: boolean) => ReactNode);
  scaleTo?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const reduce = useReducedMotion();
  const scale = useSharedValue(1);
  const [pressed, setPressed] = useState(false);
  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));
  return (
    <Pressable
      {...props}
      onPressIn={(e) => {
        setPressed(true);
        if (!reduce) scale.set(withTiming(scaleTo, { duration: motion.press }));
        props.onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        if (!reduce) scale.set(withTiming(1, { duration: motion.press }));
        props.onPressOut?.(e);
      }}
      style={style}>
      <Animated.View style={animated}>{typeof children === 'function' ? children(pressed) : children}</Animated.View>
    </Pressable>
  );
}

/** Glass card (surface). Pass onPress to make the whole card tappable with a gentle press-in. */
export function Card({
  children,
  style,
  onPress,
  accessibilityLabel,
  tier = 'mid',
  padded = true,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  accessibilityLabel?: string;
  tier?: GlassTier;
  padded?: boolean;
}) {
  const inner = (
    <Glass tier={tier} style={onPress ? undefined : style} contentStyle={padded ? styles.cardContent : undefined}>
      {children}
    </Glass>
  );
  if (!onPress) return inner;
  return (
    <Squishable onPress={onPress} accessibilityRole="button" accessibilityLabel={accessibilityLabel} scaleTo={0.98} style={style}>
      {inner}
    </Squishable>
  );
}

/**
 * The one solid surface that breaks the glass pattern: use at most once per screen
 * for the most important number (earnings, amount due).
 */
export function FeaturedCard({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const { colors, shadows } = useTheme();
  return (
    <View
      style={[
        { backgroundColor: colors.featured, borderRadius: radius.card, padding: spacing.xl, gap: spacing.sm, boxShadow: shadows.featured },
        style,
      ]}>
      {children}
    </View>
  );
}

export function Row({ children, style, gap = spacing.sm }: { children: ReactNode; style?: StyleProp<ViewStyle>; gap?: number }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap }, style]}>{children}</View>;
}

export function Divider() {
  const { colors } = useTheme();
  return <View style={{ height: 1, backgroundColor: colors.hairline, marginVertical: spacing.md }} />;
}

// =================================================================== clay controls
type ButtonKind = 'primary' | 'secondary' | 'danger' | 'ghost';

/** Solid clay button (never glass). Bulges out at rest, presses in and squishes on touch. */
export function Button({
  title,
  onPress,
  kind = 'primary',
  size = 'md',
  loading,
  disabled,
  icon,
  style,
}: {
  title: string;
  onPress: () => void;
  kind?: ButtonKind;
  size?: 'sm' | 'md';
  loading?: boolean;
  disabled?: boolean;
  icon?: IconName;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors: c, shadows } = useTheme();
  const inactive = !!(disabled || loading);
  const look = {
    primary: { bg: c.accent, fg: c.onAccent, shadow: shadows.clayAccent },
    secondary: { bg: c.clay, fg: c.text, shadow: shadows.clayRaised },
    danger: { bg: c.dangerSoft, fg: c.danger, shadow: shadows.clayRaised },
    ghost: { bg: 'transparent', fg: c.accent, shadow: undefined },
  }[kind];
  return (
    <Squishable
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: inactive, busy: !!loading }}
      disabled={inactive}
      onPress={onPress}
      style={style}>
      {(pressed) => (
        <View
          style={[
            styles.button,
            {
              height: controlHeight[size],
              backgroundColor: pressed && kind === 'primary' ? c.accentPressed : look.bg,
              boxShadow: look.shadow ? (pressed ? shadows.clayPressed : look.shadow) : undefined,
              opacity: inactive ? 0.5 : 1,
            },
          ]}>
          {loading ? (
            <ActivityIndicator color={look.fg} />
          ) : (
            <Row gap={spacing.sm}>
              {icon ? <Ionicons name={icon} size={19} color={look.fg} /> : null}
              <RNText style={{ color: look.fg, fontFamily: fonts.heading, fontSize: size === 'sm' ? 14 : 16, letterSpacing: 0.3 }}>
                {title}
              </RNText>
            </Row>
          )}
        </View>
      )}
    </Squishable>
  );
}

/** Round clay button for icons (map toggle, close, delete). */
export function IconButton({
  icon,
  onPress,
  label,
  tone = 'neutral',
  size = controlHeight.sm,
  disabled,
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  tone?: Tone;
  size?: number;
  disabled?: boolean;
}) {
  const { colors: c, shadows } = useTheme();
  const t = useTone(tone);
  return (
    <Squishable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={disabled ? () => {} : onPress}
      hitSlop={6}>
      {(pressed) => (
        <View
          style={{
            width: size,
            height: size,
            borderRadius: size / 2,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: c.clay,
            boxShadow: disabled ? undefined : pressed ? shadows.clayPressed : shadows.clayRaised,
            opacity: disabled ? 0.35 : 1,
          }}>
          <Ionicons name={icon} size={size * 0.45} color={tone === 'neutral' ? c.text : t.fg} />
        </View>
      )}
    </Squishable>
  );
}

/** Recessed clay input: pressed into the surface; lifts to a clean raised field on focus. */
export function TextField({ label, error, hint, style, ...props }: TextInputProps & { label: string; error?: string; hint?: string }) {
  const { colors: c, shadows } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: spacing.xs + 2, marginBottom: spacing.lg }}>
      <Text variant="small" style={{ color: c.text, fontFamily: fonts.bodyBold }}>
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={c.muted}
        {...props}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        style={[
          styles.input,
          {
            color: c.text,
            backgroundColor: focused ? c.clay : c.clayRecessed,
            boxShadow: focused ? shadows.clayRaised : shadows.clayPressed,
            borderColor: error ? c.danger : focused ? c.accent : 'transparent',
          },
          props.multiline && { minHeight: 112, textAlignVertical: 'top', paddingTop: 16 },
          style,
        ]}
      />
      {error ? (
        <Text variant="small" style={{ color: c.danger }}>
          {error}
        </Text>
      ) : hint ? (
        <Text variant="small">{hint}</Text>
      ) : null}
    </View>
  );
}

/** Clay pill. Unselected bulges out; selected is pressed in and tinted. */
export function Chip({ label, selected, onPress, icon }: { label: string; selected: boolean; onPress: () => void; icon?: IconName }) {
  const { colors: c, shadows } = useTheme();
  return (
    <Squishable accessibilityRole="checkbox" accessibilityState={{ checked: selected }} accessibilityLabel={label} onPress={onPress}>
      {(pressed) => (
        <View
          style={[
            styles.chip,
            {
              backgroundColor: selected ? c.accentSoft : c.clay,
              boxShadow: selected || pressed ? shadows.clayPressed : shadows.clayRaised,
            },
          ]}>
          {icon ? <Ionicons name={icon} size={15} color={selected ? c.accent : c.muted} /> : null}
          <RNText style={{ color: selected ? c.accent : c.text, fontFamily: selected ? fonts.bodyBold : fonts.bodyMedium, fontSize: 14 }}>
            {label}
          </RNText>
        </View>
      )}
    </Squishable>
  );
}

/** Static clay tag (non-interactive), e.g. amenities. */
export function Tag({ label, icon }: { label: string; icon?: IconName }) {
  const { colors: c, shadows } = useTheme();
  return (
    <View style={[styles.chip, { backgroundColor: c.clay, boxShadow: shadows.clayRaised }]}>
      {icon ? <Ionicons name={icon} size={15} color={c.accent} /> : null}
      <RNText style={{ color: c.text, fontFamily: fonts.bodyMedium, fontSize: 14 }}>{label}</RNText>
    </View>
  );
}

/** Clay switch: recessed track, raised knob. */
export function Toggle({ label, value, onChange, hint }: { label: string; value: boolean; onChange: (v: boolean) => void; hint?: string }) {
  const { colors: c, shadows } = useTheme();
  const reduce = useReducedMotion();
  const x = useSharedValue(value ? 1 : 0);
  useEffect(() => {
    x.set(reduce ? (value ? 1 : 0) : withTiming(value ? 1 : 0, { duration: 180 }));
  }, [value, reduce, x]);
  const knob = useAnimatedStyle(() => ({ transform: [{ translateX: x.get() * 22 }] }));
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={label}
      onPress={() => onChange(!value)}
      style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm, gap: spacing.md }}>
      <View style={{ flex: 1 }}>
        <Text style={{ fontFamily: fonts.bodyMedium }}>{label}</Text>
        {hint ? <Text variant="small">{hint}</Text> : null}
      </View>
      <View style={[styles.track, { backgroundColor: value ? c.accentSoft : c.clayRecessed, boxShadow: shadows.clayPressed }]}>
        <Animated.View style={[styles.thumb, { backgroundColor: value ? c.accent : c.clayKnob, boxShadow: shadows.clayKnob }, knob]} />
      </View>
    </Pressable>
  );
}

/** Circular clay orb holding an icon — used instead of emoji or decorative glyphs. */
export function IconOrb({ icon, tone = 'accent', size = 52 }: { icon: IconName; tone?: Tone; size?: number }) {
  const { shadows } = useTheme();
  const t = useTone(tone);
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: t.bg,
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: shadows.clayRaised,
      }}>
      <Ionicons name={icon} size={size * 0.46} color={t.fg} />
    </View>
  );
}

// =================================================================== states
export function Loading({ label = 'Loading' }: { label?: string }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.center, { backgroundColor: colors.canvas }]} accessibilityLabel={label}>
      <ActivityIndicator size="large" color={colors.accent} />
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Backdrop>
      <View style={[styles.center, { gap: spacing.lg }]}>
        <IconOrb icon="cloud-offline-outline" tone="danger" size={64} />
        <Text style={{ textAlign: 'center' }}>{message}</Text>
        {onRetry ? <Button title="Try again" kind="secondary" onPress={onRetry} /> : null}
      </View>
    </Backdrop>
  );
}

export function EmptyState({ icon, title, body, action }: { icon: IconName; title: string; body?: string; action?: ReactNode }) {
  return (
    <View style={[styles.center, { gap: spacing.md, paddingVertical: spacing.xxl }]}>
      <IconOrb icon={icon} size={68} />
      <Text variant="heading" style={{ textAlign: 'center', marginTop: spacing.sm }}>
        {title}
      </Text>
      {body ? (
        <Text variant="muted" style={{ textAlign: 'center', maxWidth: 300 }}>
          {body}
        </Text>
      ) : null}
      {action ? <View style={{ marginTop: spacing.sm, alignSelf: 'stretch' }}>{action}</View> : null}
    </View>
  );
}

/** Light-glass notice with a clay icon orb in the semantic tone. */
export function Banner({ tone, children }: { tone: 'info' | 'warning' | 'danger' | 'success'; children: ReactNode }) {
  const t = useTone(tone);
  const icons: Record<typeof tone, IconName> = {
    info: 'information-circle',
    warning: 'time',
    danger: 'alert-circle',
    success: 'checkmark-circle',
  };
  return (
    <Glass tier="light" rounded={radius.md} contentStyle={styles.banner}>
      <View accessibilityRole="alert" style={{ flexDirection: 'row', gap: spacing.md, alignItems: 'center' }}>
        <IconOrb icon={icons[tone]} tone={tone} size={32} />
        <View style={{ flex: 1 }}>
          {typeof children === 'string' ? <Text style={{ color: t.fg, fontFamily: fonts.bodyMedium }}>{children}</Text> : children}
        </View>
      </View>
    </Glass>
  );
}

const STATUS_TONE: Record<BookingStatus, Tone> = {
  pending_approval: 'warning',
  pending_payment: 'warning',
  confirmed: 'info',
  checked_in: 'success',
  completed: 'neutral',
  cancelled: 'neutral',
  rejected: 'danger',
  expired: 'neutral',
};

/** Clay status pill; meaning is carried by the text, colour only reinforces it. */
export function Pill({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  const { shadows } = useTheme();
  const t = useTone(tone);
  return (
    <View style={[styles.pill, { backgroundColor: t.bg, boxShadow: shadows.clayRaised }]}>
      <RNText style={{ color: t.fg, fontFamily: fonts.heading, fontSize: 12, letterSpacing: 0.3 }}>{label}</RNText>
    </View>
  );
}

export function StatusBadge({ status }: { status: BookingStatus }) {
  return <Pill label={STATUS_LABEL[status]} tone={STATUS_TONE[status]} />;
}

export function StatusText({ label }: { label: string }) {
  return <Pill label={label} />;
}

export function PriceRow({ label, value, strong, inverse }: { label: string; value: string; strong?: boolean; inverse?: boolean }) {
  const { colors } = useTheme();
  return (
    <Row style={{ justifyContent: 'space-between', paddingVertical: 4 }} gap={spacing.md}>
      <Text
        variant={strong ? 'body' : 'muted'}
        style={[{ flexShrink: 1 }, strong && { fontFamily: fonts.heading }, inverse && { color: colors.onFeaturedMuted }]}>
        {label}
      </Text>
      <Text style={[{ textAlign: 'right', flexShrink: 1 }, strong && { fontFamily: fonts.heading }, inverse && { color: colors.onFeatured }]}>
        {value}
      </Text>
    </Row>
  );
}

export function Section({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <View style={{ gap: spacing.md, marginTop: spacing.xl }}>
      <Row style={{ justifyContent: 'space-between', minHeight: 24 }}>
        <Text variant="label">{title}</Text>
        {right}
      </Row>
      {children}
    </View>
  );
}

export function ListItem({
  icon,
  title,
  subtitle,
  onPress,
  danger,
}: {
  icon: IconName;
  title: string;
  subtitle?: string;
  onPress: () => void;
  danger?: boolean;
}) {
  const { colors: c } = useTheme();
  return (
    <Squishable accessibilityRole="button" accessibilityLabel={title} onPress={onPress} scaleTo={0.98}>
      <Glass tier="light" rounded={radius.md} contentStyle={styles.listItem}>
        <IconOrb icon={icon} tone={danger ? 'danger' : 'accent'} size={40} />
        <View style={{ flex: 1 }}>
          <Text style={[{ fontFamily: fonts.bodyMedium }, danger && { color: c.danger }]}>{title}</Text>
          {subtitle ? <Text variant="small">{subtitle}</Text> : null}
        </View>
        <Ionicons name="chevron-forward" size={18} color={c.muted} />
      </Glass>
    </Squishable>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: 120 },
  cardContent: { padding: spacing.xl, gap: spacing.sm },
  button: { borderRadius: radius.control, paddingHorizontal: spacing.xl, alignItems: 'center', justifyContent: 'center' },
  input: {
    minHeight: controlHeight.md,
    borderRadius: radius.control,
    borderWidth: 1.5,
    paddingHorizontal: spacing.lg + 2,
    paddingVertical: 14,
    fontSize: 16,
    fontFamily: fonts.body,
  },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: radius.pill, paddingHorizontal: 16, minHeight: 40, margin: 3 },
  track: { width: 56, height: 34, borderRadius: 17, padding: 4 },
  thumb: { width: 26, height: 26, borderRadius: 13 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  banner: { padding: spacing.md },
  pill: { borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 5, alignSelf: 'flex-start' },
  listItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, padding: spacing.md, paddingRight: spacing.lg },
});
