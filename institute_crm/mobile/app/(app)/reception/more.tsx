import MoreScreen from '@/screens/MoreScreen';

/**
 * Re-export, not `export { default } from ...`: Expo Router's route manifest is
 * built by a Babel pass that looks for a real `export default` in the file. A
 * re-export of `default` is not detected, and the route is dropped with
 * "missing the required default export".
 */
export default MoreScreen;
