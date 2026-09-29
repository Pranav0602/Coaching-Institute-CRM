/**
 * Ambient declarations for Metro asset imports.
 *
 * These live here rather than in `expo-env.d.ts` because Expo deletes and
 * regenerates that file on `expo start` - anything in it is not durable.
 */
declare module '*.ttf' {
  const value: number;
  export default value;
}

declare module '*.otf' {
  const value: number;
  export default value;
}
