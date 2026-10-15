import { Alert, Platform } from 'react-native';

/**
 * Cross-platform dialogs. React Native's Alert.alert is a no-op on web, so any action placed
 * behind it (delete, archive, cancel...) silently never runs there. On web these use the
 * browser's own confirm/alert, which are blocking and accessible; on iOS/Android, Alert.
 */

/** Ask before a destructive action. `onConfirm` runs only if the user confirms. */
export function confirmAction(
  title: string,
  message: string,
  onConfirm: () => void,
  { confirmLabel = title, cancelLabel = 'Keep' }: { confirmLabel?: string; cancelLabel?: string } = {},
): void {
  if (Platform.OS === 'web') {
    if (globalThis.confirm?.(`${title}\n\n${message}`)) onConfirm();
    return;
  }
  Alert.alert(title, message, [
    { text: cancelLabel, style: 'cancel' },
    { text: confirmLabel, style: 'destructive', onPress: onConfirm },
  ]);
}

/** Tell the user something, then run `onDismiss` (always, on every platform). */
export function notify(title: string, message: string, onDismiss?: () => void): void {
  if (Platform.OS === 'web') {
    globalThis.alert?.(`${title}\n\n${message}`);
    onDismiss?.();
    return;
  }
  Alert.alert(title, message, [{ text: 'OK', onPress: onDismiss }], { onDismiss });
}
