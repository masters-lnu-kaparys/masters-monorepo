import type { Decision, Observation, PolicyRuntime, SamplingPolicy } from "./types.ts";

const EDGES = [60, 300, 900, 3600, 14400];

function validatePolicy(policy: SamplingPolicy) {
  if (policy.schema_version !== 1 || !Number.isSafeInteger(policy.allocation_seed)
    || JSON.stringify(policy.observed_run_edges_seconds) !== JSON.stringify(EDGES)) {
    throw new Error("Unsupported sampling policy");
  }
  const names = Object.keys(policy.component_weights).sort();
  if (names.length === 0 || names.join() !== Object.keys(policy.components).sort().join()
    || Object.values(policy.component_weights).some(w => !Number.isFinite(w) || w < 0)
    || Math.abs(Object.values(policy.component_weights).reduce((a, b) => a + b, 0) - 1) > 1e-9) {
    throw new Error("Invalid sampling weights");
  }
  for (const component of Object.values(policy.components)) {
    if (!Number.isFinite(component.lambdaF) || !Number.isFinite(component.lambdaO)
      || component.lambdaF <= 0 || component.lambdaO <= 0) throw new Error("Invalid penalties");
    for (const row of [component.pooled_fallback, ...Object.values(component.bay_tables)]) {
      if (row.length !== 48 || row.some(d => !Number.isInteger(d) || d < 1 || d > 300)) {
        throw new Error("Invalid sampling table");
      }
    }
  }
}

/** Matches the frozen Python runtime: SHA-256, first eight bytes, little endian. */
export async function componentForBay(policy: SamplingPolicy, bayId: number): Promise<string> {
  if (!Number.isSafeInteger(bayId)) throw new Error("Invalid bay identifier");
  const bytes = new TextEncoder().encode(`local-risk-allocation:${policy.allocation_seed}:${bayId}`);
  const hash = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes));
  let integer = 0n;
  for (let i = 7; i >= 0; i--) integer = (integer << 8n) | BigInt(hash[i]);
  const fraction = Number(integer) / 2 ** 64;
  const names = Object.keys(policy.component_weights).sort();
  let cumulative = 0;
  for (const name of names) {
    cumulative += policy.component_weights[name];
    if (fraction < cumulative) return name;
  }
  return names[names.length - 1];
}

export function observationContext(observation: Readonly<Observation>) {
  const { time, state, observedRunStart } = observation;
  if (!Number.isSafeInteger(time) || !Number.isSafeInteger(observedRunStart)
    || time < 0 || observedRunStart < 0 || observedRunStart > time || (state !== 0 && state !== 1)) {
    throw new Error("Invalid measured observation");
  }
  const clockBin = Math.floor((time % 86400) / 21600);
  const runBin = EDGES.filter(edge => time - observedRunStart >= edge).length;
  return { clockBin, runBin, contextIndex: (state * 4 + clockBin) * 6 + runBin };
}

export async function createPolicyRuntime(policy: SamplingPolicy, bayId: number): Promise<PolicyRuntime> {
  validatePolicy(policy);
  const componentId = await componentForBay(policy, bayId);
  const component = policy.components[componentId];
  const local = component.bay_tables[String(bayId)];
  // Copy the table into the closure so callers cannot mutate an active policy.
  const table = [...(local ?? component.pooled_fallback)];
  return {
    componentId,
    component,
    usesLocalHistory: local !== undefined,
    decide(observation): Decision {
      const context = observationContext(observation);
      const pauseSeconds = table[context.contextIndex];
      return { ...observation, ...context, pauseSeconds, nextTime: observation.time + pauseSeconds };
    },
  };
}
