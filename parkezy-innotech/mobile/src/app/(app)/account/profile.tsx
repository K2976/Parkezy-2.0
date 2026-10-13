import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';

import { ApiError, errorMessage } from '@/api/client';
import { meApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { Banner, Button, Screen, TextField } from '@/ui/components';

export default function Profile() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.full_name ?? '');
  const [phone, setPhone] = useState(user?.phone ?? '');
  const save = useMutation({
    mutationFn: () => meApi.update({ full_name: name.trim(), phone: phone.trim() || null }),
    onSuccess: (u) => {
      setUser(u);
      router.back();
    },
  });
  const fieldErrors = save.error instanceof ApiError ? save.error.fieldErrors : {};
  return (
    <Screen>
      {save.error ? <Banner tone="danger">{errorMessage(save.error)}</Banner> : null}
      <TextField label="Full name" value={name} onChangeText={setName} autoComplete="name" error={fieldErrors.full_name} />
      <TextField label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91 98765 43210" error={fieldErrors.phone} />
      <Button title="Save" onPress={() => save.mutate()} loading={save.isPending} disabled={name.trim().length < 2} />
    </Screen>
  );
}
