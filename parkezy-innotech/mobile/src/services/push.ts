import { isRunningInExpoGo } from 'expo';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

import { meApi } from '@/api/endpoints';

let registered: { token: string; platform: 'ios' | 'android' } | null = null;

type NotificationsModule = typeof import('expo-notifications');

function getNotifications(): NotificationsModule | null {
  if (isRunningInExpoGo()) {
    return null;
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require('expo-notifications') as NotificationsModule;
  } catch {
    return null;
  }
}

const notifications = getNotifications();

if (notifications) {
  notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

function projectId(): string | undefined {
  return Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
}

/**
 * Ask for notification permission (call this in context, e.g. right after a booking) and
 * register the device with the backend. Returns false when push isn't possible here
 * (simulator, permission denied, Expo Go without a project id) — the in-app inbox still works.
 */
export async function registerForPush(): Promise<boolean> {
  if (Platform.OS !== 'ios' && Platform.OS !== 'android') return false;
  if (!Device.isDevice || !projectId()) return false;
  if (!notifications) return false;

  if (Platform.OS === 'android') {
    await notifications.setNotificationChannelAsync('default', {
      name: 'Bookings',
      importance: notifications.AndroidImportance.MAX,
    });
  }
  const current = await notifications.getPermissionsAsync();
  const status = current.status === 'granted' ? current.status : (await notifications.requestPermissionsAsync()).status;
  if (status !== 'granted') return false;
  try {
    const { data } = await notifications.getExpoPushTokenAsync({ projectId: projectId() });
    registered = { token: data, platform: Platform.OS };
    await meApi.addPushToken(data, Platform.OS);
    return true;
  } catch {
    return false;
  }
}

export async function unregisterPushToken(): Promise<void> {
  if (!registered) return;
  await meApi.removePushToken(registered.token, registered.platform);
  registered = null;
}
