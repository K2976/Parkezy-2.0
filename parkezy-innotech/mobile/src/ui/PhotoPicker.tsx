import Ionicons from '@expo/vector-icons/Ionicons';
import { Image } from 'expo-image';
import { useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { pickImages, type Purpose, uploadImage } from '@/services/uploads';
import { Banner, Button, IconButton, Row, Text } from '@/ui/components';
import { radius, spacing, useTheme } from '@/ui/theme';

export type UploadedPhoto = { localUri: string; uploadId: string | null; failed?: boolean };

/** Picks photos and uploads each one straight away so the final submit is instant. */
export function PhotoPicker({ photos, onChange, max, purpose }: {
  photos: UploadedPhoto[];
  onChange: (updater: (prev: UploadedPhoto[]) => UploadedPhoto[]) => void;
  max: number;
  purpose: Purpose;
}) {
  const { colors: c, shadows } = useTheme();
  const [error, setError] = useState<string | null>(null);
  const remaining = max - photos.length;

  const upload = async (localUri: string, mimeType: string, size?: number) => {
    try {
      const uploadId = await uploadImage({ uri: localUri, mimeType, size }, purpose);
      onChange((prev) => prev.map((p) => (p.localUri === localUri ? { ...p, uploadId, failed: false } : p)));
    } catch (e) {
      setError(errorMessage(e));
      onChange((prev) => prev.map((p) => (p.localUri === localUri ? { ...p, failed: true } : p)));
    }
  };

  const add = async (source: 'camera' | 'library') => {
    setError(null);
    try {
      const picked = await pickImages(source, remaining);
      const fresh = picked.slice(0, remaining);
      onChange((prev) => [...prev, ...fresh.map((p) => ({ localUri: p.uri, uploadId: null }))]);
      await Promise.all(fresh.map((p) => upload(p.uri, p.mimeType, p.size)));
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <View style={{ gap: spacing.md }}>
      <Row style={{ flexWrap: 'wrap' }} gap={spacing.lg}>
        {photos.map((p) => (
          <View key={p.localUri} style={{ width: 96, height: 96, borderRadius: radius.control, boxShadow: shadows.clayRaised }}>
            <Image source={{ uri: p.localUri }} style={{ width: 96, height: 96, borderRadius: radius.control }} accessibilityLabel="Selected photo" />
            {!p.uploadId && !p.failed ? (
              <View style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center', backgroundColor: c.scrim, borderRadius: radius.control }}>
                <ActivityIndicator color={c.onScrim} />
              </View>
            ) : null}
            {p.failed ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Retry upload"
                onPress={() => upload(p.localUri, 'image/jpeg')}
                style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center', backgroundColor: c.scrim, borderRadius: radius.control }}>
                <Ionicons name="refresh" size={24} color={c.onScrim} />
              </Pressable>
            ) : null}
            <View style={{ position: 'absolute', top: -8, right: -8 }}>
              <IconButton
                icon="close"
                tone="danger"
                size={30}
                label="Remove photo"
                onPress={() => onChange((prev) => prev.filter((x) => x.localUri !== p.localUri))}
              />
            </View>
          </View>
        ))}
      </Row>
      {error ? <Banner tone="danger">{error}</Banner> : null}
      {remaining > 0 ? (
        <Row>
          <Button title="Take photo" kind="secondary" icon="camera-outline" onPress={() => add('camera')} style={{ flex: 1 }} />
          <Button title="Choose" kind="secondary" icon="images-outline" onPress={() => add('library')} style={{ flex: 1 }} />
        </Row>
      ) : (
        <Text variant="small">Maximum {max} photos.</Text>
      )}
    </View>
  );
}
