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

/**
 * Floating strong-glass dock. The active tab is a clay well pressed into the glass;
 * inactive tabs are flat so the active one reads instantly.
 */
export function GlassTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const { colors, shadows } = useTheme();
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
      }}>
      <Glass
        tier="strong"
        rounded={radius.card}
        style={{
          borderBottomLeftRadius: 0,
          borderBottomRightRadius: 0,
          borderLeftWidth: 0,
          borderRightWidth: 0,
          borderBottomWidth: 0,
        }}
        contentStyle={{
          flexDirection: 'row',
          paddingTop: 8,
          paddingBottom: bottomPadding,
          paddingHorizontal: spacing.sm,
          alignItems: 'center',
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
          return (
            <Squishable
              key={route.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={badge ? `${label}, ${badge} new` : label}
              onPress={onPress}
              style={{ flex: 1, alignItems: 'center' }}>
              <View
                style={{
                  alignItems: 'center',
                  justifyContent: 'center',
                  paddingVertical: 5,
                  paddingHorizontal: 14,
                  borderRadius: radius.pill,
                  backgroundColor: focused ? colors.clayRecessed : 'transparent',
                  boxShadow: focused ? shadows.clayPressed : undefined,
                  gap: 2,
                  minWidth: 60,
                }}>
                <Ionicons name={TAB_ICONS[route.name] ?? 'ellipse-outline'} size={22} color={focused ? colors.accent : colors.muted} />
                <RNText style={{ fontFamily: focused ? fonts.heading : fonts.bodyMedium, fontSize: 11, color: focused ? colors.accent : colors.muted }}>
                  {label}
                </RNText>
                {badge ? (
                  <View
                    style={{
                      position: 'absolute',
                      top: 1,
                      right: 4,
                      minWidth: 18,
                      height: 18,
                      borderRadius: 9,
                      paddingHorizontal: 4,
                      backgroundColor: colors.danger,
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                    <RNText style={{ color: colors.onAccent, fontFamily: fonts.bodyBold, fontSize: 10 }}>{badge}</RNText>
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
