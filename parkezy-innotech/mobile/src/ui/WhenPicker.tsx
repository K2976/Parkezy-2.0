import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Modal, Platform, ScrollView, View } from 'react-native';

import type { PublicConfig } from '@/api/types';
import { Button, Chip, Row, Text } from '@/ui/components';
import { Glass } from '@/ui/Glass';
import { radius, spacing, useColors } from '@/ui/theme';
import { dateTime, duration } from '@/utils/format';
import { addMinutes, currentStepStart, durationOptions, roundUpToStep } from '@/utils/time';

export type Window = { start: Date; minutes: number };

export function defaultWindow(config: PublicConfig): Window {
  const preferred = 120;
  const minutes = Math.min(Math.max(preferred, config.min_booking_minutes), config.max_booking_minutes);
  return { start: currentStepStart(new Date(), config.booking_step_minutes), minutes };
}

export function windowIso(w: Window): { starts_at: string; ends_at: string } {
  return { starts_at: w.start.toISOString(), ends_at: addMinutes(w.start, w.minutes).toISOString() };
}

/** Start time + duration, constrained by the server's booking rules. */
export function WhenPicker({ config, value, onChange }: {
  config: PublicConfig;
  value: Window;
  onChange: (w: Window) => void;
}) {
  const c = useColors();
  const [iosOpen, setIosOpen] = useState(false);
  const [draft, setDraft] = useState(value.start);
  const step = config.booking_step_minutes;
  const now = new Date();
  const maxDate = addMinutes(now, config.max_advance_days * 24 * 60);
  const isNow = value.start.getTime() === currentStepStart(now, step).getTime();

  const apply = (date: Date) => onChange({ ...value, start: roundUpToStep(date, step) });

  const openPicker = () => {
    if (Platform.OS === 'android') {
      DateTimePickerAndroid.open({
        value: value.start,
        mode: 'date',
        minimumDate: now,
        maximumDate: maxDate,
        onChange: (event, date) => {
          if (event.type !== 'set' || !date) return;
          DateTimePickerAndroid.open({
            value: date,
            mode: 'time',
            onChange: (e2, time) => {
              if (e2.type === 'set' && time) apply(time);
            },
          });
        },
      });
    } else {
      setDraft(value.start);
      setIosOpen(true);
    }
  };

  return (
    <View style={{ gap: spacing.sm }}>
      <Row style={{ flexWrap: 'wrap' }} gap={spacing.xs}>
        <Chip label="Now" selected={isNow} onPress={() => onChange({ ...value, start: currentStepStart(new Date(), step) })} />
        <Chip label={isNow ? 'Later…' : dateTime(value.start.toISOString())} selected={!isNow} onPress={openPicker} />
      </Row>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingVertical: 4, paddingHorizontal: 2 }}>
        {durationOptions(config.min_booking_minutes, config.max_booking_minutes, step).map((m) => (
          <Chip key={m} label={duration(m)} selected={value.minutes === m} onPress={() => onChange({ ...value, minutes: m })} />
        ))}
      </ScrollView>
      <Modal visible={iosOpen} transparent animationType="slide" onRequestClose={() => setIosOpen(false)}>
        <View style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: c.scrim, padding: spacing.md }}>
          <Glass tier="strong" rounded={radius.card} contentStyle={{ padding: spacing.xl, gap: spacing.md }}>
            <Text variant="heading">Start time</Text>
            <DateTimePicker
              value={draft}
              mode="datetime"
              display="spinner"
              minuteInterval={step as 1 | 5 | 10 | 15 | 20 | 30}
              minimumDate={now}
              maximumDate={maxDate}
              onChange={(_, d) => d && setDraft(d)}
            />
            <Button
              title="Done"
              onPress={() => {
                apply(draft);
                setIosOpen(false);
              }}
            />
          </Glass>
        </View>
      </Modal>
    </View>
  );
}
