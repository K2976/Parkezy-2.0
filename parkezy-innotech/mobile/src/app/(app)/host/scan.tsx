import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { View } from 'react-native';

import { errorMessage } from '@/api/client';
import { hostApi } from '@/api/endpoints';
import type { AccessVerifyResult } from '@/api/types';
import { keys } from '@/hooks/queries';
import { Banner, Button, Card, Chip, Loading, PriceRow, Row, Screen, Section, Text, TextField } from '@/ui/components';
import { Segmented } from '@/ui/Segmented';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { money, time } from '@/utils/format';

/** Hosts verify drivers on the server: a signed one-time QR, or the listing + 6-digit PIN. */
export default function ScanAccess() {
  const queryClient = useQueryClient();
  const { shadows } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const [mode, setMode] = useState<'qr' | 'pin'>('qr');
  const [pin, setPin] = useState('');
  const [listingId, setListingId] = useState<string | null>(null);
  const [result, setResult] = useState<AccessVerifyResult | null>(null);
  const handling = useRef(false);
  const listings = useQuery({ queryKey: keys.hostListings, queryFn: hostApi.listings });

  const verify = useMutation({
    mutationFn: hostApi.verifyAccess,
    onSuccess: (r) => {
      setResult(r);
      setPin('');
      queryClient.invalidateQueries({ queryKey: ['host'] });
    },
    onSettled: () => {
      handling.current = false;
    },
  });

  const onScan = (data: string) => {
    if (handling.current || verify.isPending || result) return;
    handling.current = true;
    verify.mutate({ qr_token: data });
  };

  const reset = () => {
    setResult(null);
    verify.reset();
  };

  if (result) {
    const b = result.booking;
    const tz = b.listing.timezone;
    return (
      <Screen>
        <Banner tone="success">{result.action === 'checked_in' ? 'Driver checked in' : 'Driver checked out'}</Banner>
        <Card style={{ marginTop: spacing.md }}>
          <Text variant="heading">{b.driver.full_name}</Text>
          <PriceRow label="Slot" value={b.slot.label} />
          {b.vehicle_number ? <PriceRow label="Vehicle" value={b.vehicle_number} /> : null}
          <PriceRow label="Booked until" value={time(b.ends_at, tz)} />
          {result.action === 'checked_out' ? (
            <>
              {b.overstay_minutes ? <PriceRow label={`Overstay (${b.overstay_minutes} min)`} value={money(b.overstay_fee, b.currency)} /> : null}
              <PriceRow label="Total" value={money(b.final_amount ?? b.total_amount, b.currency)} strong />
              {b.payment_mode === 'pay_at_venue' ? (
                <Text style={{ fontFamily: fonts.bodyBold }}>Collect {money(b.final_amount ?? b.total_amount, b.currency)} from the driver.</Text>
              ) : Number(b.amount_due) > 0 ? (
                <Text variant="small">The driver pays the remaining {money(b.amount_due, b.currency)} in the app.</Text>
              ) : (
                <Text variant="small">Already paid in the app.</Text>
              )}
            </>
          ) : null}
        </Card>
        <View style={{ gap: spacing.sm, marginTop: spacing.lg }}>
          <Button title="Scan another" onPress={reset} />
          <Button title="Done" kind="secondary" onPress={() => router.back()} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <Segmented
        options={[
          { key: 'qr', label: 'Scan QR' },
          { key: 'pin', label: 'Enter PIN' },
        ]}
        value={mode}
        onChange={setMode}
      />
      {verify.error ? (
        <View style={{ marginTop: spacing.md }}>
          <Banner tone="danger">{errorMessage(verify.error)}</Banner>
        </View>
      ) : null}

      {mode === 'qr' ? (
        <View style={{ marginTop: spacing.md, gap: spacing.md }}>
          {!permission ? (
            <Loading />
          ) : !permission.granted ? (
            <>
              <Text variant="muted">Allow camera access to scan the driver’s QR code.</Text>
              <Button title="Allow camera" onPress={requestPermission} />
            </>
          ) : (
            <View style={{ height: 340, borderRadius: radius.card, overflow: 'hidden', boxShadow: shadows.clayRaised }}>
              <CameraView
                style={{ flex: 1 }}
                facing="back"
                barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
                onBarcodeScanned={verify.isPending ? undefined : ({ data }) => onScan(data)}
                accessibilityLabel="Camera viewfinder for QR codes"
              />
            </View>
          )}
          <Text variant="small">Ask the driver to open their booking and show the QR code.</Text>
        </View>
      ) : (
        <View style={{ marginTop: spacing.md }}>
          <Section title="Which spot?">
            <Row style={{ flexWrap: 'wrap' }}>
              {(listings.data ?? []).map((l) => (
                <Chip key={l.id} label={l.title} selected={listingId === l.id} onPress={() => setListingId(l.id)} />
              ))}
            </Row>
          </Section>
          <View style={{ height: spacing.md }} />
          <TextField label="Driver’s PIN" value={pin} onChangeText={setPin} keyboardType="number-pad" maxLength={8} />
          <Button
            title="Verify"
            onPress={() => verify.mutate({ listing_id: listingId!, pin })}
            loading={verify.isPending}
            disabled={!listingId || pin.length < 4}
          />
        </View>
      )}
    </Screen>
  );
}
