import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { Modal, Pressable, ScrollView, TextInput, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { hostApi } from '@/api/endpoints';
import type { AccessVerifyResult } from '@/api/types';
import { keys } from '@/hooks/queries';
import { Banner, Button, Card, IconButton, Loading, PriceRow, Row, Screen, Text, TextField } from '@/ui/components';
import { Segmented } from '@/ui/Segmented';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { money, time } from '@/utils/format';

/** Hosts verify drivers on the server: a signed one-time QR, or the driver's 6-digit PIN. */
export default function ScanAccess() {
  const queryClient = useQueryClient();
  const { colors: c, shadows } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const [mode, setMode] = useState<'qr' | 'pin'>('pin');
  const [pin, setPin] = useState('');
  const [listingId, setListingId] = useState<string | null>(null);
  const [showSpotModal, setShowSpotModal] = useState(false);
  const [spotSearch, setSpotSearch] = useState('');
  const [result, setResult] = useState<AccessVerifyResult | null>(null);
  const pinInputRef = useRef<TextInput | null>(null);
  const handling = useRef(false);
  const listings = useQuery({ queryKey: keys.hostListings, queryFn: hostApi.listings });

  const verify = useMutation({
    mutationFn: hostApi.verifyAccess,
    onSuccess: (r) => {
      setResult(r);
      setPin('');
      queryClient.invalidateQueries({ queryKey: ['host'] });
    },
    // Clear the boxes after a failed PIN so the host can simply type it again.
    onError: () => setPin(''),
    onSettled: () => {
      handling.current = false;
    },
  });
  const errorCode = verify.error instanceof ApiError ? verify.error.code : null;
  const pendingBookingId =
    verify.error instanceof ApiError ? (verify.error.details as { booking_id?: string } | undefined)?.booking_id : undefined;

  const onScan = (data: string) => {
    if (handling.current || verify.isPending || result) return;
    handling.current = true;
    verify.mutate({ qr_token: data });
  };

  const handleDigitPress = (digit: string) => {
    if (pin.length < 6) {
      const next = pin + digit;
      setPin(next);
      if (next.length === 6) {
        verify.mutate({ pin: next, listing_id: listingId ?? undefined });
      }
    }
  };

  const handleBackspace = () => {
    setPin((prev) => prev.slice(0, -1));
  };

  const handleClear = () => {
    setPin('');
  };

  const reset = () => {
    setResult(null);
    setPin('');
    verify.reset();
  };

  const allListings = listings.data ?? [];
  const selectedListing = allListings.find((l) => l.id === listingId);
  const filteredListings = allListings.filter((l) =>
    l.title.toLowerCase().includes(spotSearch.toLowerCase()) ||
    l.address_line.toLowerCase().includes(spotSearch.toLowerCase())
  );

  if (result) {
    const b = result.booking;
    const tz = b.listing.timezone;
    return (
      <Screen>
        <Banner tone="success">{result.action === 'checked_in' ? '✓ Driver Checked In' : '✓ Driver Checked Out'}</Banner>
        <Card style={{ marginTop: spacing.md }}>
          <Text variant="heading">{b.driver.full_name}</Text>
          <PriceRow label="Spot" value={b.listing.title} />
          <PriceRow label="Slot" value={b.slot.label} />
          {b.vehicle_number ? <PriceRow label="Vehicle" value={b.vehicle_number} /> : null}
          <PriceRow label="Booked until" value={time(b.ends_at, tz)} />
          {result.action === 'checked_out' ? (
            <>
              {b.overstay_minutes ? <PriceRow label={`Overstay (${b.overstay_minutes} min)`} value={money(b.overstay_fee, b.currency)} /> : null}
              <PriceRow label="Total" value={money(b.final_amount ?? b.total_amount, b.currency)} strong />
              {b.payment_mode === 'pay_at_venue' ? (
                <Text style={{ fontFamily: fonts.bodyBold, color: c.accent, marginTop: spacing.sm }}>
                  Collect {money(b.final_amount ?? b.total_amount, b.currency)} cash/UPI from the driver.
                </Text>
              ) : Number(b.amount_due) > 0 ? (
                <Text variant="small">The driver pays the remaining {money(b.amount_due, b.currency)} in the app.</Text>
              ) : (
                <Text variant="small">Already paid in the app.</Text>
              )}
            </>
          ) : (
            <Text variant="small" style={{ marginTop: spacing.sm, color: c.muted }}>
              Driver may now park in slot {b.slot.label}.
            </Text>
          )}
        </Card>
        <View style={{ gap: spacing.sm, marginTop: spacing.lg }}>
          <Button title="Verify another driver" onPress={reset} />
          <Button title="Done" kind="secondary" onPress={() => router.back()} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <Segmented
        options={[
          { key: 'pin', label: 'Enter PIN' },
          { key: 'qr', label: 'Scan QR' },
        ]}
        value={mode}
        onChange={setMode}
      />

      {verify.error ? (
        <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
          <Banner tone={errorCode === 'too_early' || errorCode === 'needs_approval' ? 'warning' : 'danger'}>
            {errorMessage(verify.error)}
          </Banner>
          {errorCode === 'needs_approval' && pendingBookingId ? (
            <Button
              title="Review this request"
              kind="secondary"
              size="sm"
              onPress={() => router.push({ pathname: '/booking/[id]', params: { id: pendingBookingId } })}
            />
          ) : null}
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
        <View style={{ marginTop: spacing.md, gap: spacing.md }}>
          {/* Clean spot selector header (auto-detects spot by default) */}
          <Card tier="light">
            <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text variant="label">Target Facility</Text>
                <Text style={{ fontFamily: fonts.bodyBold }} numberOfLines={1}>
                  {selectedListing ? selectedListing.title : 'All Spots (Auto-Detect Booking)'}
                </Text>
                <Text variant="small" style={{ color: c.muted }}>
                  {selectedListing ? `${selectedListing.city}` : 'PIN will be matched against all your active spots'}
                </Text>
              </View>
              <Row gap={spacing.xs}>
                {selectedListing ? (
                  <IconButton
                    icon="close"
                    size={32}
                    label="Clear spot filter"
                    onPress={() => setListingId(null)}
                  />
                ) : null}
                <Button
                  title={selectedListing ? 'Change' : 'Filter spot'}
                  kind="secondary"
                  size="sm"
                  onPress={() => setShowSpotModal(true)}
                />
              </Row>
            </Row>
          </Card>

          {/* Hidden text input for native keyboard support */}
          <TextInput
            ref={pinInputRef}
            value={pin}
            onChangeText={(val) => {
              const cleaned = val.replace(/\D/g, '').slice(0, 6);
              setPin(cleaned);
              if (cleaned.length === 6) {
                verify.mutate({ pin: cleaned, listing_id: listingId ?? undefined });
              }
            }}
            keyboardType="number-pad"
            maxLength={6}
            style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }}
            autoFocus
          />

          {/* 6 Digit Display Wells */}
          <Pressable onPress={() => pinInputRef.current?.focus()}>
            <Row gap={spacing.sm} style={{ justifyContent: 'center', marginVertical: spacing.sm }}>
              {[0, 1, 2, 3, 4, 5].map((idx) => {
                const char = pin[idx];
                const isActive = pin.length === idx;
                const isFilled = Boolean(char);
                return (
                  <View
                    key={idx}
                    style={{
                      width: 48,
                      height: 60,
                      borderRadius: radius.md,
                      backgroundColor: isFilled ? c.clay : c.clayRecessed,
                      borderWidth: isActive ? 2.5 : isFilled ? 1.5 : 1,
                      borderColor: isActive ? c.accent : isFilled ? c.text : c.hairline,
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: isActive ? shadows.clayRaised : shadows.clayPressed,
                    }}>
                    <Text style={{ fontFamily: fonts.display, fontSize: 26, color: c.text }}>
                      {char || ''}
                    </Text>
                  </View>
                );
              })}
            </Row>
          </Pressable>

          <Text variant="small" style={{ textAlign: 'center', color: c.muted }}>
            Ask driver for their 6-digit access PIN shown on their booking screen
          </Text>

          {/* Interactive On-Screen Number Pad */}
          <View style={{ gap: spacing.sm, marginVertical: spacing.xs }}>
            {[
              ['1', '2', '3'],
              ['4', '5', '6'],
              ['7', '8', '9'],
              ['C', '0', '⌫'],
            ].map((row, rIdx) => (
              <Row key={rIdx} gap={spacing.sm} style={{ justifyContent: 'center' }}>
                {row.map((key) => {
                  const isAction = key === 'C' || key === '⌫';
                  return (
                    <Pressable
                      key={key}
                      onPress={() => {
                        if (key === 'C') handleClear();
                        else if (key === '⌫') handleBackspace();
                        else handleDigitPress(key);
                      }}
                      style={({ pressed }) => ({
                        flex: 1,
                        maxWidth: 96,
                        height: 52,
                        borderRadius: radius.md,
                        backgroundColor: pressed || isAction ? c.clayRecessed : c.clay,
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderWidth: 1,
                        borderColor: c.hairline,
                        boxShadow: pressed ? shadows.clayPressed : shadows.clayRaised,
                      })}>
                      {key === '⌫' ? (
                        <Ionicons name="backspace-outline" size={22} color={c.text} />
                      ) : (
                        <Text style={{ fontFamily: fonts.heading, fontSize: 20, color: isAction ? c.muted : c.text }}>
                          {key}
                        </Text>
                      )}
                    </Pressable>
                  );
                })}
              </Row>
            ))}
          </View>

          <Button
            title={verify.isPending ? 'Verifying PIN…' : pin.length === 6 ? 'Verify PIN & Check In / Out' : `Enter PIN (${pin.length}/6)`}
            onPress={() => verify.mutate({ pin, listing_id: listingId ?? undefined })}
            loading={verify.isPending}
            disabled={pin.length < 6 || verify.isPending}
          />
        </View>
      )}

      {/* Spot Selection Modal */}
      <Modal visible={showSpotModal} animationType="slide" transparent>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: c.canvas, borderTopLeftRadius: radius.card, borderTopRightRadius: radius.card, maxHeight: '80%', padding: spacing.lg, gap: spacing.md }}>
            <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <Text variant="heading">Filter by Spot</Text>
              <IconButton icon="close" label="Close" onPress={() => setShowSpotModal(false)} />
            </Row>
            <TextField
              label="Search spots"
              placeholder="Filter your spots by name or address…"
              value={spotSearch}
              onChangeText={setSpotSearch}
            />
            <ScrollView style={{ maxHeight: 350 }}>
              <Pressable
                onPress={() => {
                  setListingId(null);
                  setShowSpotModal(false);
                }}
                style={{ paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: c.hairline }}>
                <Text style={{ fontFamily: fonts.bodyBold, color: !listingId ? c.accent : c.text }}>
                  ✓ All Spots (Auto-Detect)
                </Text>
                <Text variant="small" style={{ color: c.muted }}>Search across all your active reservations</Text>
              </Pressable>
              {filteredListings.map((l) => (
                <Pressable
                  key={l.id}
                  onPress={() => {
                    setListingId(l.id);
                    setShowSpotModal(false);
                  }}
                  style={{ paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: c.hairline }}>
                  <Text style={{ fontFamily: fonts.bodyBold, color: listingId === l.id ? c.accent : c.text }}>
                    {l.title}
                  </Text>
                  <Text variant="small" style={{ color: c.muted }}>{l.address_line}, {l.city}</Text>
                </Pressable>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}
