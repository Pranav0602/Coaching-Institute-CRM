/**
 * Deep links out of the app: dialler, WhatsApp, email, share sheet.
 *
 * `Linking.canOpenURL` is checked before every launch and the result respected.
 * On iOS a scheme absent from `LSApplicationQueriesSchemes` always reports
 * `false`, and on Android an app that is not installed throws rather than
 * returning `false`, so a missing handler has to degrade to a "tell the user"
 * path instead of a crash.
 */
import * as Clipboard from 'expo-clipboard';
import { Alert, Linking, Share } from 'react-native';

import { normalisePhone } from './format';

const canOpen = async (url: string): Promise<boolean> => {
  try {
    return await Linking.canOpenURL(url);
  } catch {
    return false;
  }
};

const openOrExplain = async (url: string, fallbackMessage: string): Promise<boolean> => {
  try {
    if (!(await canOpen(url))) {
      Alert.alert('Not available', fallbackMessage);
      return false;
    }
    await Linking.openURL(url);
    return true;
  } catch {
    Alert.alert('Could not open', fallbackMessage);
    return false;
  }
};

export const callPhone = async (phone: string | null | undefined): Promise<boolean> => {
  const number = normalisePhone(phone);
  if (!number) {
    Alert.alert('No phone number', 'This contact has no phone number on file.');
    return false;
  }
  return openOrExplain(`tel:${number}`, 'This device cannot place phone calls.');
};

/**
 * `whatsapp://` opens the installed app; `https://wa.me` is the fallback for
 * regions where WhatsApp lives only in the browser.
 */
export const openWhatsApp = async (phone: string | null | undefined, message = ''): Promise<boolean> => {
  const number = normalisePhone(phone).replace('+', '');
  if (!number) {
    Alert.alert('No phone number', 'This contact has no phone number on file.');
    return false;
  }
  const text = encodeURIComponent(message);
  const opened = await openOrExplain(
    `whatsapp://send?phone=${number}&text=${text}`,
    'WhatsApp is not installed on this device.',
  );
  if (opened) return true;
  return openOrExplain(`https://wa.me/${number}?text=${text}`, 'No messaging app is available.');
};

export const sendEmail = async (
  address: string | null | undefined,
  subject = '',
  body = '',
): Promise<boolean> => {
  if (!address) {
    Alert.alert('No email address', 'This contact has no email address on file.');
    return false;
  }
  const url = `mailto:${address}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  return openOrExplain(url, 'No email app is set up on this device.');
};

export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await Clipboard.setStringAsync(text);
    return true;
  } catch {
    Alert.alert('Copy failed', 'Could not write to the clipboard.');
    return false;
  }
};

export const shareText = async (message: string, title = 'Share'): Promise<boolean> => {
  try {
    const result = await Share.share({ message, title });
    return result.action === Share.sharedAction;
  } catch {
    return false;
  }
};

export const openExternal = async (url: string | null | undefined): Promise<boolean> => {
  if (!url) {
    Alert.alert('No link', 'This record has no attachment.');
    return false;
  }
  try {
    await Linking.openURL(url);
    return true;
  } catch {
    Alert.alert('Could not open link', url);
    return false;
  }
};
