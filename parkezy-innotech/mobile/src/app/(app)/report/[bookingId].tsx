import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { ApiError, errorMessage } from '@/api/client';
import { disputeApi } from '@/api/endpoints';
import { keys, useConfig } from '@/hooks/queries';
import { Banner, Button, Chip, Loading, Row, Screen, Section, Text, TextField } from '@/ui/components';
import { PhotoPicker, type UploadedPhoto } from '@/ui/PhotoPicker';
import { spacing } from '@/ui/theme';
import { titleCase } from '@/utils/format';

export default function ReportProblem() {
  const { bookingId } = useLocalSearchParams<{ bookingId: string }>();
  const config = useConfig();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [photos, setPhotos] = useState<UploadedPhoto[]>([]);
  const submit = useMutation({
    mutationFn: () =>
      disputeApi.create({
        booking_id: bookingId,
        reason: reason!,
        description: description.trim(),
        evidence_upload_ids: photos.map((p) => p.uploadId!).filter(Boolean),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.disputes });
      router.back();
    },
  });

  if (!config.data) return <Loading />;
  const uploading = photos.some((p) => !p.uploadId && !p.failed);
  const fieldErrors = submit.error instanceof ApiError ? submit.error.fieldErrors : {};

  return (
    <Screen>
      <Text variant="muted">Tell us what went wrong. Our team reviews every report and replies by email.</Text>
      <Section title="What happened?">
        <Row style={{ flexWrap: 'wrap' }}>
          {config.data.dispute_reasons.map((r) => (
            <Chip key={r} label={titleCase(r)} selected={reason === r} onPress={() => setReason(r)} />
          ))}
        </Row>
      </Section>
      <Section title="Details">
        <TextField label="Describe the problem" value={description} onChangeText={setDescription} multiline maxLength={4000} error={fieldErrors.description} hint="At least 10 characters" />
      </Section>
      <Section title="Photos (optional)">
        <PhotoPicker photos={photos} onChange={setPhotos} max={config.data.max_dispute_photos} purpose="dispute_evidence" />
      </Section>
      {submit.error ? <Banner tone="danger">{errorMessage(submit.error)}</Banner> : null}
      <Button
        title="Send report"
        style={{ marginTop: spacing.xl }}
        onPress={() => submit.mutate()}
        loading={submit.isPending}
        disabled={!reason || description.trim().length < 10 || uploading}
      />
    </Screen>
  );
}
