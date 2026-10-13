import { View } from 'react-native';

import type { Listing, ListingInput, PublicConfig } from '@/api/types';
import { Chip, Row, Section, Text, TextField, Toggle } from '@/ui/components';
import { spacing } from '@/ui/theme';
import { titleCase, WEEKDAYS } from '@/utils/format';

/** Editable listing details, shared by "new listing" and "manage listing". */
export type ListingDraft = {
  title: string;
  description: string;
  access_instructions: string;
  hourly_rate: string;
  daily_cap: string;
  amenities: string[];
  auto_accept: boolean;
  is_24h: boolean;
  open_time: string;
  close_time: string;
  open_days: number[];
};

export const ALL_DAYS = [1, 2, 3, 4, 5, 6, 7];
const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
const PRICE = /^\d{1,8}(\.\d{1,2})?$/;

export function emptyDraft(): ListingDraft {
  return {
    title: '',
    description: '',
    access_instructions: '',
    hourly_rate: '',
    daily_cap: '',
    amenities: [],
    auto_accept: true,
    is_24h: true,
    open_time: '08:00',
    close_time: '20:00',
    open_days: ALL_DAYS,
  };
}

export function draftFrom(l: Listing): ListingDraft {
  return {
    title: l.title,
    description: l.description ?? '',
    access_instructions: l.access_instructions ?? '',
    hourly_rate: l.hourly_rate,
    daily_cap: l.daily_cap ?? '',
    amenities: l.amenities,
    auto_accept: l.auto_accept,
    is_24h: l.is_24h,
    open_time: l.open_time?.slice(0, 5) ?? '08:00',
    close_time: l.close_time?.slice(0, 5) ?? '20:00',
    open_days: l.open_days,
  };
}

/** Client-side checks mirror the server's so users get instant feedback; the server still decides. */
export function validateDraft(d: ListingDraft): Record<string, string> {
  const errors: Record<string, string> = {};
  if (d.title.trim().length < 3) errors.title = 'Give your spot a short name (3+ characters)';
  if (!PRICE.test(d.hourly_rate) || Number(d.hourly_rate) <= 0) errors.hourly_rate = 'Enter a price like 40 or 49.50';
  if (d.daily_cap && (!PRICE.test(d.daily_cap) || Number(d.daily_cap) <= 0)) errors.daily_cap = 'Enter a valid amount';
  if (!d.is_24h) {
    if (!HHMM.test(d.open_time)) errors.open_time = 'Use 24-hour HH:MM';
    if (!HHMM.test(d.close_time)) errors.close_time = 'Use 24-hour HH:MM';
    if (!errors.open_time && !errors.close_time && d.open_time >= d.close_time) errors.close_time = 'Must be after opening time';
  }
  if (!d.open_days.length) errors.open_days = 'Pick at least one day';
  return errors;
}

export function draftToInput(d: ListingDraft): ListingInput {
  return {
    title: d.title.trim(),
    description: d.description.trim() || null,
    access_instructions: d.access_instructions.trim() || null,
    hourly_rate: d.hourly_rate,
    daily_cap: d.daily_cap || null,
    amenities: d.amenities,
    auto_accept: d.auto_accept,
    is_24h: d.is_24h,
    open_time: d.is_24h ? null : d.open_time,
    close_time: d.is_24h ? null : d.close_time,
    open_days: d.open_days,
  };
}

export function ListingFields({ draft, onChange, errors, config }: {
  draft: ListingDraft;
  onChange: (d: ListingDraft) => void;
  errors: Record<string, string>;
  config: PublicConfig;
}) {
  const set = <K extends keyof ListingDraft>(key: K, value: ListingDraft[K]) => onChange({ ...draft, [key]: value });
  const toggleIn = <T,>(list: T[], item: T) => (list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);
  return (
    <View>
      <TextField label="Name" value={draft.title} onChangeText={(v) => set('title', v)} placeholder="Covered driveway near MG Road" error={errors.title} maxLength={120} />
      <TextField label="Description (optional)" value={draft.description} onChangeText={(v) => set('description', v)} multiline maxLength={4000} />
      <TextField
        label="How to get in (shown only to confirmed drivers)"
        value={draft.access_instructions}
        onChangeText={(v) => set('access_instructions', v)}
        multiline
        placeholder="Gate code, which bay, who to ask…"
        maxLength={2000}
      />
      <Row style={{ alignItems: 'flex-start' }} gap={spacing.md}>
        <View style={{ flex: 1 }}>
          <TextField
            label={`Price per hour (${config.currency})`}
            value={draft.hourly_rate}
            onChangeText={(v) => set('hourly_rate', v.replace(',', '.'))}
            keyboardType="decimal-pad"
            error={errors.hourly_rate}
          />
        </View>
        <View style={{ flex: 1 }}>
          <TextField
            label="Max per day (optional)"
            value={draft.daily_cap}
            onChangeText={(v) => set('daily_cap', v.replace(',', '.'))}
            keyboardType="decimal-pad"
            error={errors.daily_cap}
          />
        </View>
      </Row>
      <Toggle
        label="Instant booking"
        hint={draft.auto_accept ? 'Drivers are confirmed immediately' : 'You approve each request'}
        value={draft.auto_accept}
        onChange={(v) => set('auto_accept', v)}
      />
      <Section title="Amenities">
        <Row style={{ flexWrap: 'wrap' }}>
          {config.amenities.map((a) => (
            <Chip key={a} label={titleCase(a)} selected={draft.amenities.includes(a)} onPress={() => set('amenities', toggleIn(draft.amenities, a))} />
          ))}
        </Row>
      </Section>
      <Section title="Availability">
        <Toggle label="Open 24 hours" value={draft.is_24h} onChange={(v) => set('is_24h', v)} />
        {!draft.is_24h ? (
          <Row style={{ alignItems: 'flex-start' }} gap={spacing.md}>
            <View style={{ flex: 1 }}>
              <TextField label="Opens" value={draft.open_time} onChangeText={(v) => set('open_time', v)} placeholder="08:00" error={errors.open_time} maxLength={5} />
            </View>
            <View style={{ flex: 1 }}>
              <TextField label="Closes" value={draft.close_time} onChangeText={(v) => set('close_time', v)} placeholder="20:00" error={errors.close_time} maxLength={5} />
            </View>
          </Row>
        ) : null}
        <Row style={{ flexWrap: 'wrap' }}>
          {WEEKDAYS.map((day, i) => (
            <Chip key={day} label={day} selected={draft.open_days.includes(i + 1)} onPress={() => set('open_days', toggleIn(draft.open_days, i + 1).sort())} />
          ))}
        </Row>
        {errors.open_days ? <Text variant="small">{errors.open_days}</Text> : null}
      </Section>
    </View>
  );
}
