/**
 * Parkezy design tokens — "Glass surfaces, clay controls".
 *
 *  - Surfaces (cards, panels, tab bar, banners) are frosted GLASS in three tiers.
 *  - Controls (buttons, inputs, chips, toggles, badges, icon orbs) are matte CLAY:
 *    solid fills with multi-layer shadow stacks that bulge out (convex) or press in (concave).
 *  - No gradients, no emoji, soft desaturated colours. Charcoal text never lighter than `muted`.
 *
 * Every visual value used by components lives here; components never hard-code colours.
 */

const light = {
  // canvas & text
  canvas: '#FFFFFF',
  text: '#1C1924',
  muted: '#666173', // lightest allowed text colour (WCAG AA on canvas)
  // accent (soft violet) and semantic hues, deliberately desaturated
  accent: '#6E5BC4',
  accentPressed: '#5F4DB3',
  onAccent: '#FFFFFF',
  accentSoft: '#EFEBF9',
  info: '#3F7FAE',
  infoSoft: '#E7F0F7',
  success: '#2F8A6A',
  successSoft: '#E3F2EC',
  warning: '#A86F1C',
  warningSoft: '#FBF2E3',
  danger: '#B4485C',
  dangerSoft: '#FCECEF',
  // clay materials
  clay: '#FFFFFF', // clean white raised control surface
  clayRecessed: '#F2F0F7', // pressed-in surface (inputs, tracks)
  clayKnob: '#FFFFFF',
  // glass materials (fill tiers per the glass formula)
  glassStrong: 'rgba(255,255,255,0.88)',
  glassMid: 'rgba(255,255,255,0.72)',
  glassLight: 'rgba(255,255,255,0.52)',
  glassBorder: 'rgba(215,210,230,0.50)',
  glassHighlight: 'rgba(255,255,255,0.95)',
  // the one solid "featured" surface that breaks the glass pattern
  featured: '#2E2A35',
  onFeatured: '#FFFFFF',
  onFeaturedMuted: '#C9C3D3',
  // ambient background blobs (solid, low opacity, never gradients)
  blobA: 'rgba(139,120,214,0.12)',
  blobB: 'rgba(216,139,170,0.08)',
  blobC: 'rgba(127,179,217,0.10)',
  hairline: 'rgba(51,47,58,0.06)',
  scrim: 'rgba(30,27,36,0.45)',
  onScrim: '#FFFFFF',
  qrBackground: '#FFFFFF', // QR codes must stay dark-on-white to scan reliably
  qrForeground: '#1B1822',
};

type Palette = typeof light;

const dark: Palette = {
  canvas: '#17151C',
  text: '#ECE9F2',
  muted: '#ABA5B6',
  accent: '#A495E6',
  accentPressed: '#9283D8',
  onAccent: '#1B1822',
  accentSoft: '#2C2740',
  info: '#86B6DA',
  infoSoft: '#1D2A36',
  success: '#7CC6A8',
  successSoft: '#1B2E27',
  warning: '#DDB271',
  warningSoft: '#33291A',
  danger: '#E08C9B',
  dangerSoft: '#371F25',
  clay: '#25222C',
  clayRecessed: '#1D1A23',
  clayKnob: '#3A3643',
  glassStrong: 'rgba(42,38,50,0.62)',
  glassMid: 'rgba(42,38,50,0.48)',
  glassLight: 'rgba(42,38,50,0.34)',
  glassBorder: 'rgba(255,255,255,0.10)',
  glassHighlight: 'rgba(255,255,255,0.14)',
  featured: '#ECE9F2',
  onFeatured: '#1B1822',
  onFeaturedMuted: '#4A4553',
  blobA: 'rgba(139,120,214,0.20)',
  blobB: 'rgba(216,139,170,0.12)',
  blobC: 'rgba(127,179,217,0.14)',
  hairline: 'rgba(255,255,255,0.08)',
  scrim: 'rgba(0,0,0,0.55)',
  onScrim: '#FFFFFF',
  qrBackground: '#FFFFFF',
  qrForeground: '#1B1822',
};

/** Multi-layer shadow stacks: refined, subtle elevation that gently pops buttons without excessive halos. */
function shadowsFor(scheme: 'light' | 'dark') {
  if (scheme === 'dark') {
    return {
      clayRaised: '0 2px 4px rgba(0,0,0,0.30)',
      clayAccent: '0 2px 6px rgba(164,149,230,0.30)',
      clayPressed: undefined,
      clayKnob: '0 1px 3px rgba(0,0,0,0.40)',
      glass: '0 2px 6px rgba(0,0,0,0.20)',
      featured: '0 3px 8px rgba(0,0,0,0.30)',
    };
  }
  return {
    // Crisp, subtle drop shadow that gently pops buttons without huge blurred halos:
    clayRaised: '0 2px 4px rgba(20,15,35,0.08)',
    // Subtle accent lift just to pop accent buttons cleanly:
    clayAccent: '0 2px 6px rgba(110,91,196,0.22)',
    // Clean pressed surface (background tint handles the pressed state):
    clayPressed: undefined,
    clayKnob: '0 1px 3px rgba(20,15,35,0.12)',
    // Glass surface: clean, subtle float without foggy halos:
    glass: '0 2px 6px rgba(20,15,35,0.05)',
    featured: '0 3px 8px rgba(20,15,35,0.10)',
  };
}

export type Theme = {
  scheme: 'light' | 'dark';
  colors: Palette;
  shadows: ReturnType<typeof shadowsFor>;
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

/** Super-rounded: nothing under 20 except tiny inner details. Nested elements step down by 8. */
export const radius = { control: 20, md: 24, card: 32, hero: 48, pill: 999 } as const;

export const glassTiers = {
  strong: { fill: 'glassStrong', blur: 60 },
  mid: { fill: 'glassMid', blur: 45 },
  light: { fill: 'glassLight', blur: 30 },
} as const;
export type GlassTier = keyof typeof glassTiers;

export const fonts = {
  heading: 'Nunito_800ExtraBold',
  display: 'Nunito_900Black',
  body: 'DMSans_400Regular',
  bodyMedium: 'DMSans_500Medium',
  bodyBold: 'DMSans_700Bold',
} as const;

export const motion = {
  press: 140, // squish in/out
  pressScale: 0.94,
  floatMs: 9000, // background blob drift
} as const;

export const controlHeight = { sm: 44, md: 56 } as const;

export function useTheme(preferredScheme?: 'light' | 'dark'): Theme {
  // Light is the first and default theme; dark palette is preserved.
  const scheme: 'light' | 'dark' = preferredScheme ?? 'light';
  return { scheme, colors: scheme === 'dark' ? dark : light, shadows: shadowsFor(scheme) };
}

/** Back-compat helper used by screens that only need colours. */
export function useColors(): Palette {
  return useTheme().colors;
}

export type Colors = Palette;
