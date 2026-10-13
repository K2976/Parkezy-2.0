import * as ImagePicker from 'expo-image-picker';

import { ApiError } from '@/api/client';
import { uploadApi } from '@/api/endpoints';

export type PickedImage = { uri: string; mimeType: string; size?: number };
export type Purpose = 'listing_photo' | 'dispute_evidence' | 'avatar';

export async function pickImages(source: 'camera' | 'library', limit: number): Promise<PickedImage[]> {
  const permission =
    source === 'camera'
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) {
    throw new Error(
      source === 'camera'
        ? 'Camera access is off. Enable it in Settings to take photos.'
        : 'Photo access is off. Enable it in Settings to choose photos.',
    );
  }
  const options: ImagePicker.ImagePickerOptions = {
    mediaTypes: ['images'],
    quality: 0.7, // keeps uploads small on mobile data
    allowsMultipleSelection: source === 'library' && limit > 1,
    selectionLimit: limit,
  };
  const result =
    source === 'camera' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
  if (result.canceled) return [];
  return result.assets.map((a) => ({ uri: a.uri, mimeType: a.mimeType ?? 'image/jpeg', size: a.fileSize }));
}

/** Presign -> PUT bytes straight to object storage (Backblaze) -> confirm. Returns the upload id. */
export async function uploadImage(image: PickedImage, purpose: Purpose): Promise<string> {
  const ticket = await uploadApi.create(purpose, image.mimeType);
  if (image.size && image.size > ticket.max_bytes) {
    throw new ApiError(422, 'upload_too_large', `Photo is larger than ${Math.round(ticket.max_bytes / 1e6)} MB`);
  }
  const file = await fetch(image.uri);
  const blob = await file.blob();
  const put = await fetch(ticket.upload_url, { method: ticket.method, headers: ticket.headers, body: blob });
  if (!put.ok) throw new ApiError(put.status, 'upload_failed', 'Photo upload failed, please try again');
  await uploadApi.complete(ticket.id);
  return ticket.id;
}
