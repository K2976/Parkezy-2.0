import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError, errorMessage } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { Banner, Button, Screen, TextField } from '@/ui/components';
import { notify } from '@/ui/dialogs';

export default function ChangePassword() {
  const { signOut } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const change = useMutation({
    mutationFn: () => authApi.changePassword({ current_password: current, new_password: next }),
    // The server ends every session after a password change.
    onSuccess: () => notify('Password updated', 'Please sign in again.', () => signOut()),
  });
  const fieldErrors = change.error instanceof ApiError ? change.error.fieldErrors : {};
  return (
    <Screen>
      {change.error ? <Banner tone="danger">{errorMessage(change.error)}</Banner> : null}
      <TextField label="Current password" value={current} onChangeText={setCurrent} secureTextEntry autoComplete="current-password" />
      <TextField
        label="New password"
        value={next}
        onChangeText={setNext}
        secureTextEntry
        autoComplete="new-password"
        hint="At least 8 characters with letters and numbers"
        error={fieldErrors.new_password}
      />
      <Button title="Update password" onPress={() => change.mutate()} loading={change.isPending} disabled={!current || next.length < 8} />
    </Screen>
  );
}
