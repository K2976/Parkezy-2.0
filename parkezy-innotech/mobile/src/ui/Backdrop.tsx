import { BlurTargetView, BlurView } from 'expo-blur';
import { createContext, type ReactNode, type RefObject, useContext, useEffect, useRef } from 'react';
import { StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { motion, useTheme } from '@/ui/theme';

/**
 * Android only blurs what is inside a BlurTargetView, so every screen renders its ambient
 * background into one and shares the ref with the glass panels drawn above it.
 */
const BlurTargetContext = createContext<RefObject<View | null> | null>(null);

export function useBlurTarget() {
  return useContext(BlurTargetContext);
}

export function BlurTargetProvider({ target, children }: { target: RefObject<View | null>; children: ReactNode }) {
  return <BlurTargetContext.Provider value={target}>{children}</BlurTargetContext.Provider>;
}

function Blob({ color, size, top, left, delay, lift, tilt }: {
  color: string;
  size: number;
  top: number;
  left: number;
  delay: number;
  lift: number;
  tilt: number;
}) {
  const reduce = useReducedMotion();
  const t = useSharedValue(0);
  useEffect(() => {
    if (reduce) return;
    t.set(
      withDelay(
        delay,
        withRepeat(withTiming(1, { duration: motion.floatMs, easing: Easing.inOut(Easing.sin) }), -1, true),
      ),
    );
  }, [reduce, delay, t]);
  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: -lift * t.get() }, { rotate: `${tilt * t.get()}deg` }],
  }));
  return (
    <Animated.View
      pointerEvents="none"
      style={[{ position: 'absolute', width: size, height: size, borderRadius: size / 2, backgroundColor: color, top, left }, style]}
    />
  );
}

/** Canvas + slowly drifting soft blobs, frosted so they read as ambient light, not shapes. */
export function Backdrop({ children }: { children: ReactNode }) {
  const { colors, scheme } = useTheme();
  const { width, height } = useWindowDimensions();
  const target = useRef<View | null>(null);
  const size = height * 0.6;
  return (
    <View style={{ flex: 1, backgroundColor: colors.canvas }}>
      <BlurTargetView ref={target} style={StyleSheet.absoluteFill} pointerEvents="none">
        <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.canvas }]} />
        <Blob color={colors.blobA} size={size} top={-size * 0.25} left={-size * 0.3} delay={0} lift={20} tilt={2} />
        <Blob color={colors.blobB} size={size * 0.8} top={height * 0.25} left={width - size * 0.45} delay={2000} lift={15} tilt={-2} />
        <Blob color={colors.blobC} size={size * 0.9} top={height * 0.62} left={-size * 0.2} delay={4000} lift={30} tilt={5} />
      </BlurTargetView>
      {/* Frost the blobs into ambient light. Sits outside the target so Android can blur it. */}
      <BlurView
        intensity={90}
        tint={scheme === 'dark' ? 'dark' : 'light'}
        blurTarget={target}
        blurMethod="dimezisBlurViewSdk31Plus"
        pointerEvents="none"
        style={StyleSheet.absoluteFill}
      />
      <BlurTargetProvider target={target}>{children}</BlurTargetProvider>
    </View>
  );
}
