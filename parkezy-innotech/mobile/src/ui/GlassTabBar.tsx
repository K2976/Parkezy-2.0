import Ionicons from '@expo/vector-icons/Ionicons';
import type { Tabs } from 'expo-router';
import type { ComponentProps } from 'react';
import { Text as RNText, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { type IconName, Squishable } from '@/ui/components';
import { Glass } from '@/ui/Glass';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';

/** Props expo-router passes to a custom tab bar (derived so we don't depend on internal paths). */
type BottomTabBarProps = Parameters<NonNullable<ComponentProps<typeof Tabs>['tabBar']>>[0];

export const TAB_ICONS: Record<string, IconName> = {
  index: 'map-outline',
  bookings: 'calendar-outline',
  host: 'home-outline',
  account: 'person-circle-outline',
};

export const TAB_ACTIVE_ICONS: Record<string, IconName> = {
  index: 'map',
  bookings: 'calendar',
  host: 'home',
  account: 'person-circle',
};

/**
 * Floating strong-glass dock with rounded capsule bubbles for the active tab.
 * Uses overflow: 'hidden' and smooth pill geometry to prevent square clipping on Android Expo Go.
 */
export function GlassTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const { colors, shadows, scheme } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomPadding = Math.max(insets.bottom, 10);

  return (
    <View
      pointerEvents="box-none"
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        alignItems: 'center',
        paddingHorizontal: spacing.md,
        paddingBottom: bottomPadding,
      }}>
      <Glass
        tier="strong"
        rounded={32}
        style={{
          width: '100%',
          maxWidth: 480,
          borderRadius: 32,
          overflow: 'hidden',
          borderColor: scheme === 'dark' ? 'rgba(255,255,255,0.14)' : 'rgba(215,210,230,0.65)',
          borderWidth: 1.2,
        }}
        contentStyle={{
          flexDirection: 'row',
          paddingVertical: 6,
          paddingHorizontal: spacing.xs,
          alignItems: 'center',
          justifyContent: 'space-around',
          borderRadius: 32,
          overflow: 'hidden',
        }}>
        {state.routes.map((route, index) => {
          const { options } = descriptors[route.key];
          const focused = state.index === index;
          const label = typeof options.tabBarLabel === 'string' ? options.tabBarLabel : (options.title ?? route.name);
          const badge = options.tabBarBadge;
          const onPress = () => {
            const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
            if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
          };
          const iconName = focused
            ? (TAB_ACTIVE_ICONS[route.name] ?? TAB_ICONS[route.name] ?? 'ellipse')
            : (TAB_ICONS[route.name] ?? 'ellipse-outline');

          return (
            <Squishable
              key={route.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={badge ? `${label}, ${badge} new` : label}
              onPress={onPress}
              scaleTo={0.94}
              style={{ flex: 1, alignItems: 'center' }}>
              <View
                style={{
                  alignItems: 'center',
                  justifyContent: 'center',
                  // Fixed size so every tab's bubble is the same shape regardless of label length.
                  width: 76,
                  height: 50,
                  borderRadius: radius.pill,
                  backgroundColor: focused ? colors.clayRecessed : 'transparent',
                  boxShadow: focused ? shadows.clayPressed : undefined,
                  borderWidth: focused ? 1 : 0,
                  borderColor: focused ? colors.glassBorder : 'transparent',
                  overflow: 'hidden',
                  gap: 2,
                }}>
                <Ionicons name={iconName} size={21} color={focused ? colors.accent : colors.muted} />
                <RNText
                  numberOfLines={1}
                  style={{
                    fontFamily: focused ? fonts.heading : fonts.bodyMedium,
                    fontSize: 11,
                    color: focused ? colors.accent : colors.muted,
                    letterSpacing: 0.2,
                  }}>
                  {label}
                </RNText>
                {badge ? (
                  <View
                    style={{
                      position: 'absolute',
                      top: 2,
                      right: 4,
                      minWidth: 16,
                      height: 16,
                      borderRadius: 8,
                      paddingHorizontal: 3,
                      backgroundColor: colors.danger,
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                    <RNText style={{ color: colors.onAccent, fontFamily: fonts.bodyBold, fontSize: 9 }}>{badge}</RNText>
                  </View>
                ) : null}
              </View>
            </Squishable>
          );
        })}
      </Glass>
    </View>
  );
}
