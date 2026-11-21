import test from 'node:test';
import assert from 'node:assert/strict';
import { maintainConnection } from '../src/api/realtime.ts';

test('a failed initial start retries and recovers without reloading the page', async () => {
  let starts = 0;
  let retry;
  const statuses = [];
  const connection = {
    start: async () => { if (++starts === 1) throw new Error('temporary outage'); },
    stop: async () => {},
    onreconnecting() {}, onreconnected() {}, onclose() {},
  };
  const stop = maintainConnection(connection, value => statuses.push(value), 1,
    callback => { retry = callback; return 1; }, () => {});
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(statuses, [false]);
  retry();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(starts, 2);
  assert.deepEqual(statuses, [false, true]);
  stop();
});

test('a final close restarts the connection; unmount cancels pending retries', async () => {
  let close;
  let retry;
  let cancelled = false;
  let starts = 0;
  const connection = {
    start: async () => { starts++; }, stop: async () => {},
    onreconnecting() {}, onreconnected() {}, onclose(callback) { close = callback; },
  };
  const stop = maintainConnection(connection, () => {}, 1,
    callback => { retry = callback; return 1; }, () => { cancelled = true; });
  await new Promise(resolve => setImmediate(resolve));
  close(); retry();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(starts, 2);
  close(); stop(); retry();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(starts, 2);
  assert.equal(cancelled, true);
});
