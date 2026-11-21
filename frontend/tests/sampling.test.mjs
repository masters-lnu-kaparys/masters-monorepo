import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { componentForBay, createPolicyRuntime, observationContext } from '../src/sampling/policy.ts';
import { actionComparisons, buildReplay, formatSourceTime, replayMetrics, replayScenario, validateScenario } from '../src/sampling/replay.ts';

const readJson = async path => JSON.parse(await readFile(new URL(path, import.meta.url), 'utf8'));
const data = await readJson('../public/data/sampling-demo.json');
const golden = await readJson('./fixtures/sampling-demo-golden.json');
const runtimes = new Map();
for (const bay of [...data.scenarios.map(s => s.bayId), 999999999]) runtimes.set(bay, await createPolicyRuntime(data.policy, bay));

test('SHA-256 policy assignment agrees with frozen Python on all 867 final bays', async () => {
  for (const [bay, expected] of golden.assignments) {
    assert.equal(await componentForBay(data.policy, bay), expected, `Bay ${bay}`);
  }
});

test('all 384 clock/age boundary and fallback vectors agree with Python', () => {
  for (const [bay, time, state, observedRunStart, expected] of golden.contexts) {
    const result = runtimes.get(bay).decide({ time, state, observedRunStart });
    assert.equal(result.pauseSeconds, expected, JSON.stringify({ bay, time, state, observedRunStart }));
  }
  assert.equal(runtimes.get(999999999).usesLocalHistory, false);
  assert.ok(data.scenarios.some(s => !runtimes.get(s.bayId).usesLocalHistory));
});

test('browser decisions and clipped metrics exactly match three independent Python traces', () => {
  for (const expected of golden.scenarios) {
    const scenario = data.scenarios.find(s => s.id === expected.id);
    const replay = buildReplay(scenario, runtimes.get(scenario.bayId));
    for (const name of ['author', 'fixed']) {
      assert.deepEqual(replay[name].map(d => [d.time, d.state, d.observedRunStart, d.pauseSeconds]), expected[name]);
      assert.deepEqual(replayMetrics(scenario, replay[name], scenario.endTime), expected.metrics[name]);
      assert.ok(replay[name].every(d => d.time < scenario.endTime), 'right endpoint is excluded');
    }
  }
});

test('explanation scores have the selected frozen table action as a minimum', () => {
  for (const scenario of data.scenarios) {
    const runtime = runtimes.get(scenario.bayId);
    for (const [bay, time, state, observedRunStart] of golden.contexts.filter(v => v[0] === scenario.bayId)) {
      assert.equal(bay, scenario.bayId);
      const decision = runtime.decide({ time, state, observedRunStart });
      const scores = actionComparisons(data, scenario, runtime, decision);
      const selected = scores.find(s => s.selected);
      assert.ok(selected.score <= Math.min(...scores.map(s => s.score)) + 1e-12);
      assert.ok(scores.every(s => s.expectedError >= 0 && s.expectedError <= s.pause + 1e-8));
    }
  }
});

test('changing unmeasured future intervals cannot change earlier decisions', () => {
  for (const scenario of data.scenarios) {
    const cutoff = scenario.startTime + 200;
    const modified = { ...scenario, segments: scenario.segments.flatMap(s => s.end <= cutoff ? [s]
      : s.start >= cutoff ? [{ ...s, state: 1 - s.state }]
        : [{ ...s, end: cutoff }, { ...s, start: cutoff, state: 1 - s.state }]) };
    const runtime = runtimes.get(scenario.bayId);
    const original = buildReplay(scenario, runtime).author.filter(d => d.time < cutoff);
    const changed = buildReplay(modified, runtime).author.filter(d => d.time < cutoff);
    assert.deepEqual(changed, original);
  }
});

test('half-open intervals, missed intermediate changes and elapsed error are integrated correctly', () => {
  const scenario = { id: 'unit', bayId: 1, startTime: 100, endTime: 220,
    initial: { author: { time: 100, state: 1, observedRunStart: 100 }, fixed: { time: 100, state: 1, observedRunStart: 100 } },
    segments: [{ start: 100, end: 130, state: 1 }, { start: 130, end: 160, state: 0 }, { start: 160, end: 220, state: 1 }] };
  const inputs = [];
  const decisions = replayScenario(scenario, observation => {
    inputs.push(Object.keys(observation).sort());
    return { ...observation, ...observationContext(observation), pauseSeconds: 60, nextTime: observation.time + 60 };
  }, scenario.initial.author);
  assert.equal(decisions.length, 2);
  assert.equal(decisions[1].state, 1, 'a measurement exactly at the transition sees the new state');
  assert.equal(decisions[1].observedRunStart, 100, 'an unobserved excursion cannot reset observed history');
  assert.deepEqual(replayMetrics(scenario, decisions, 145), { calls: 1, falseFreeSeconds: 0, falseOccupiedSeconds: 15 });
  assert.deepEqual(replayMetrics(scenario, decisions, 220), { calls: 2, falseFreeSeconds: 0, falseOccupiedSeconds: 30 });
  assert.ok(inputs.every(keys => keys.join() === 'observedRunStart,state,time'));
});

test('malformed policies, observations and gaps are rejected', async () => {
  const invalid = structuredClone(data.policy);
  Object.values(invalid.components)[0].pooled_fallback[0] = 0;
  await assert.rejects(createPolicyRuntime(invalid, 1));
  assert.throws(() => observationContext({ time: 10, state: 1, observedRunStart: 11 }));
  assert.throws(() => observationContext({ time: NaN, state: 0, observedRunStart: 0 }));
  const scenario = structuredClone(data.scenarios[0]);
  scenario.segments[0].end -= 1;
  assert.throws(() => validateScenario(scenario));
  const valid = data.scenarios[0];
  assert.throws(() => replayScenario(valid, observation => ({ ...observation, pauseSeconds: 0,
    nextTime: observation.time }), valid.initial.author));
});

test('source clocks remain civil labels regardless of the viewer timezone', () => {
  assert.equal(formatSourceTime(1575158400), '00:00:00');
});

test('all 191 frozen research artifacts and both exported assets retain their checksums', async () => {
  const delivery = await readJson('../../docs/research/adaptive-sampling/phase4-delivery-artifacts.json');
  const exported = await readJson('../../docs/research/adaptive-sampling/phase5-demo-export.json');
  for (const [path, expected] of Object.entries({ ...delivery.files, ...exported.files })) {
    const bytes = await readFile(new URL('../../' + path, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), expected, path);
  }
});
