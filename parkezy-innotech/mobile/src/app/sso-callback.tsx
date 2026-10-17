import { Redirect } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect } from 'react';

/**
 * Google sign-in returns to parkezy://sso-callback. On Android that deep link also opens this route,
 * while the sign-in screen's startSSOFlow() call finishes the sign-in. This screen only completes the
 * browser session (web) and gets out of the way: "/" lands on the app when signed in, or back on the
 * sign-in screen (which shows the result or the error) when not.
 */
export default function SSOCallback() {
  useEffect(() => {
    WebBrowser.maybeCompleteAuthSession();
  }, []);
  return <Redirect href="/" />;
}
