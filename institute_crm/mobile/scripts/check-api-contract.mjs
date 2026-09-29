/**
 * Wire-format tests for the API client.
 *
 * These exist because the client has to survive two shapes it did not choose:
 * the `{ success, message, data }` envelope, and DRF error bodies. Getting the
 * unwrap level wrong is silent - it returns a plausible object with the real
 * payload one level down - so it is worth pinning down with a test rather than
 * by inspection.
 *
 * Run with:  node scripts/check-api-contract.mjs
 *
 * Point BASE at a running backend to execute the live assertions; without one
 * the envelope assertions still run, offline.
 */
import assert from 'node:assert/strict';

const BASE = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1';

// Defaults match `seed_data.py`. Override both to point the live checks at a
// different backend without editing this file.
const USERNAME = process.env.CRM_USERNAME ?? 'counselor';
const PASSWORD = process.env.CRM_PASSWORD ?? 'Admin@123';

// ---------------------------------------------------------------- the client

/** Verbatim from src/api/client.ts */
const unwrapData = (res) => {
  const body = res ?? {};
  const data = body.data;
  return data !== undefined ? data : body;
};

const unwrapList = (res) => {
  if (!res) return [];
  if (Array.isArray(res)) return res;
  const body = res;
  const data = body.data ?? body;
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data?.results)) return data.data.results;
  return [];
};

const UNAUTHENTICATED_ENDPOINTS = [
  '/accounts/auth/login/',
  '/accounts/auth/forgot-password/',
  '/accounts/auth/reset-password/',
  '/accounts/auth/token/refresh/',
];

// ------------------------------------------------------------------ offline

let failures = 0;
const check = (name, fn) => {
  try {
    fn();
    console.log(`  ok   ${name}`);
  } catch (err) {
    failures += 1;
    console.log(`  FAIL ${name}\n       ${err.message}`);
  }
};

console.log('envelope unwrapping');
check('login payload is the inner object, not the envelope', () => {
  const envelope = {
    success: true,
    message: 'Request processed successfully',
    data: { access: 'a', refresh: 'r', user: { role_code: 'TEACHER' } },
  };
  const out = unwrapData(envelope);
  assert.equal(out.access, 'a');
  assert.equal(out.user.role_code, 'TEACHER');
  // The regression this guards: passing the whole AxiosResponse here returns the
  // envelope, and `data.access` is then undefined - the session gets wiped.
  assert.equal(unwrapData({ data: envelope }).access, undefined);
});
check('unwrapList handles a bare array', () => {
  assert.deepEqual(unwrapList([1, 2]), [1, 2]);
});
check('unwrapList handles the envelope', () => {
  assert.deepEqual(unwrapList({ success: true, data: [1, 2] }), [1, 2]);
});
check('unwrapList handles a paginated envelope', () => {
  assert.deepEqual(unwrapList({ success: true, data: { results: [3] } }), [3]);
  assert.deepEqual(unwrapList({ data: { results: [4] } }), [4]);
});
check('unwrapList survives a null body', () => {
  assert.deepEqual(unwrapList(null), []);
});

console.log('401 handling');
check('login is not treated as an expired session', () => {
  const url = '/accounts/auth/login/';
  assert.equal(
    UNAUTHENTICATED_ENDPOINTS.some((p) => url.includes(p)),
    true,
    'a wrong password must not trigger a refresh',
  );
});
check('an authenticated endpoint is refreshable', () => {
  const url = '/academics/courses/';
  assert.equal(UNAUTHENTICATED_ENDPOINTS.some((p) => url.includes(p)), false);
});

// -------------------------------------------------------------------- live

// `/healthz/` is mounted at the site root, not under the `/api/v1` prefix.
const ORIGIN = BASE.replace(/\/api\/v1\/?$/, '');

const reach = await fetch(`${ORIGIN}/healthz/`, {
  signal: AbortSignal.timeout(3000),
})
  .then((r) => r.ok)
  .catch(() => false);

if (!reach) {
  console.log(`\nskipping live assertions - no backend answering at ${ORIGIN}/healthz/`);
  console.log('start it with:  python manage.py runserver 8000');
  process.exit(failures ? 1 : 0);
}

console.log(`\nlive assertions against ${BASE}`);

const live = async (name, fn) => {
  try {
    await fn();
    console.log(`  ok   ${name}`);
  } catch (err) {
    failures += 1;
    console.log(`  FAIL ${name}\n       ${err.message}`);
  }
};

let session = null;

await live('login returns access, refresh and lifetime hints', async () => {
  const res = await fetch(`${BASE}/accounts/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  assert.equal(res.status, 200, `expected 200, got ${res.status}`);
  const body = await res.json();
  const data = unwrapData(body);
  assert.ok(data.access, 'no access token');
  assert.ok(data.refresh, 'no refresh token');
  assert.ok(data.user?.role_code, 'no role on the user payload');
  assert.ok(data.access_expires_in > 0, 'no access_expires_in');
  session = { access: data.access, refresh: data.refresh, role: data.user.role_code };
});

await live('the new access token authorises /auth/me/', async () => {
  const res = await fetch(`${BASE}/accounts/auth/me/`, {
    headers: { Authorization: `Bearer ${session.access}` },
  });
  assert.equal(res.status, 200, `expected 200, got ${res.status}`);
  const data = unwrapData(await res.json());
  assert.equal(data.role_code, session.role);
});

await live('refresh returns a usable pair and retires the old one', async () => {
  const first = unwrapData(
    await (
      await fetch(`${BASE}/accounts/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: session.refresh }),
      })
    ).json(),
  );
  assert.ok(first.access, 'refresh did not return an access token');
  assert.ok(first.refresh, 'refresh did not rotate the token');

  const replay = await fetch(`${BASE}/accounts/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: session.refresh }),
  });
  assert.equal(replay.status, 401, 'a rotated refresh token is still accepted');

  session = { ...session, access: first.access, refresh: first.refresh };
});

await live('a wrong password is a 401, not a crash', async () => {
  const res = await fetch(`${BASE}/accounts/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: USERNAME, password: 'definitely-wrong' }),
  });
  assert.equal(res.status, 401, `expected 401, got ${res.status}`);
  const body = await res.json();
  assert.equal(body.success, false);
  assert.ok(body.message, 'no human-readable message on the error body');
});

await live('published syllabi are listable and creations are refused', async () => {
  const headers = { Authorization: `Bearer ${session.access}` };
  const list = await fetch(`${BASE}/rag/documents/?category=STUDY_GUIDE`, { headers });
  assert.equal(list.status, 200);
  assert.ok(unwrapList(await list.json()).length > 0, 'no published syllabi');

  const create = await fetch(`${BASE}/rag/documents/`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'x', category: 'GENERAL', content: 'y' }),
  });
  assert.equal(create.status, 403, `a counsellor was allowed to create: ${create.status}`);
});

console.log(failures ? `\n${failures} check(s) failed` : '\nall checks passed');
process.exit(failures ? 1 : 0);

