import { observationContext } from "./policy.ts";
import type { Decision, DemoData, DemoScenario, Observation, PolicyRuntime, ReplayMetrics, Segment } from "./types.ts";

/** Civil timestamps in the source are labels, not UTC instants to convert. */
export function formatSourceTime(time: number): string {
  return new Date(Math.floor(time) * 1000).toISOString().slice(11, 19);
}

export function validateScenario(scenario: DemoScenario) {
  if (!Number.isSafeInteger(scenario.startTime) || !Number.isSafeInteger(scenario.endTime)
    || scenario.endTime <= scenario.startTime || !scenario.segments.length) throw new Error("Invalid replay interval");
  let edge = scenario.startTime;
  for (const segment of scenario.segments) {
    if (!Number.isSafeInteger(segment.start) || !Number.isSafeInteger(segment.end)
      || segment.start !== edge || segment.end <= edge || (segment.state !== 0 && segment.state !== 1)) {
      throw new Error("Replay requires a contiguous known history");
    }
    edge = segment.end;
  }
  if (edge !== scenario.endTime) throw new Error("Replay has an incomplete history");
  for (const initial of Object.values(scenario.initial)) {
    observationContext(initial);
    if (initial.time > scenario.startTime) throw new Error("Initial observation is in the future");
  }
}

export function stateAt(segments: readonly Segment[], time: number) {
  const segment = segments.find(s => s.start <= time && time < s.end);
  if (!segment) throw new Error("Measurement outside known history");
  return segment.state;
}

/** Only the simulator can read intervals; the policy receives Observation alone. */
export function replayScenario(scenario: DemoScenario, choose: (observation: Readonly<Observation>) => Decision,
  initial: Observation): Decision[] {
  validateScenario(scenario);
  function checked(observation: Observation) {
    const decision = choose(Object.freeze({ ...observation }));
    if (!Number.isInteger(decision.pauseSeconds) || decision.pauseSeconds < 1 || decision.pauseSeconds > 300
      || decision.time !== observation.time || decision.state !== observation.state
      || decision.observedRunStart !== observation.observedRunStart
      || decision.nextTime !== observation.time + decision.pauseSeconds) throw new Error("Invalid policy decision");
    return decision;
  }
  const result = [checked(initial)];
  if (result[0].nextTime < scenario.startTime) throw new Error("Initial schedule does not reach replay start");
  while (result[result.length - 1].nextTime < scenario.endTime) {
    const previous = result[result.length - 1];
    const time = previous.nextTime;
    const state = stateAt(scenario.segments, time);
    result.push(checked({ time, state, observedRunStart: state === previous.state ? previous.observedRunStart : time }));
  }
  return result;
}

export function buildReplay(scenario: DemoScenario, runtime: PolicyRuntime) {
  return {
    author: replayScenario(scenario, runtime.decide, scenario.initial.author),
    fixed: replayScenario(scenario, observation => ({ ...observation, ...observationContext(observation),
      pauseSeconds: 60, nextTime: observation.time + 60 }), scenario.initial.fixed),
  };
}

export function latestDecision(decisions: readonly Decision[], time: number): Decision {
  for (let i = decisions.length - 1; i >= 0; i--) {
    if (decisions[i].time <= time) return decisions[i];
  }
  throw new Error("Replay has no prior observation");
}

export function errorIntervals(scenario: DemoScenario, decisions: readonly Decision[], until: number): Segment[] {
  const end = Math.max(scenario.startTime, Math.min(until, scenario.endTime));
  return decisions.flatMap((decision, index) => {
    const a = Math.max(scenario.startTime, decision.time);
    const b = Math.min(end, decisions[index + 1]?.time ?? scenario.endTime);
    if (a >= b) return [];
    return scenario.segments.flatMap(segment => {
      const start = Math.max(a, segment.start);
      const stop = Math.min(b, segment.end);
      return start < stop && segment.state !== decision.state ? [{ start, end: stop, state: segment.state }] : [];
    });
  });
}

export function replayMetrics(scenario: DemoScenario, decisions: readonly Decision[], until: number): ReplayMetrics {
  const end = Math.min(until, scenario.endTime);
  const errors = errorIntervals(scenario, decisions, end);
  return {
    calls: decisions.filter(d => d.time >= scenario.startTime && d.time <= end && d.time < scenario.endTime).length,
    falseFreeSeconds: errors.filter(s => s.state === 1).reduce((sum, s) => sum + s.end - s.start, 0),
    falseOccupiedSeconds: errors.filter(s => s.state === 0).reduce((sum, s) => sum + s.end - s.start, 0),
  };
}

export function actionComparisons(data: DemoData, scenario: DemoScenario, runtime: PolicyRuntime, decision: Decision) {
  const risk = data.risk.byBay[String(scenario.bayId)] ?? data.risk.pooled;
  const costs = risk[decision.contextIndex];
  const penalty = decision.state === 0 ? runtime.component.lambdaF : runtime.component.lambdaO;
  return data.actions.map((pause, index) => ({ pause, expectedError: costs[index],
    score: (1 + penalty * costs[index]) / pause, selected: pause === decision.pauseSeconds }));
}
