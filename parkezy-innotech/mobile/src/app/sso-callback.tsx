import * as WebBrowser from 'expo-web-browser';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

export default function SSOCallback() {
  useEffect(() => {
    WebBrowser.maybeCompleteAuthSession();
  }, []);

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <ActivityIndicator size="large" />
    </View>
  );
}
