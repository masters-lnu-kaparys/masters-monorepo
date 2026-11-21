export type Occupancy = 0 | 1;

/** The complete policy input. It deliberately contains no recorded intervals. */
export type Observation = {
  time: number;
  state: Occupancy;
  observedRunStart: number;
};

export type PolicyComponent = {
  bay_tables: Record<string, number[]>;
  pooled_fallback: number[];
  lambdaF: number;
  lambdaO: number;
};

export type SamplingPolicy = {
  schema_version: number;
  allocation_seed: number;
  observed_run_edges_seconds: number[];
  component_weights: Record<string, number>;
  components: Record<string, PolicyComponent>;
};

export type Segment = { start: number; end: number; state: Occupancy };
export type DemoScenario = {
  id: string;
  bayId: number;
  startTime: number;
  endTime: number;
  dateLocal: string;
  hasLocalHistory: boolean;
  segments: Segment[];
  initial: { author: Observation; fixed: Observation };
};

export type DemoData = {
  schemaVersion: number;
  source: { title: string; url: string; license: string; clock: string; selection: string };
  policy: SamplingPolicy;
  actions: number[];
  risk: { byBay: Record<string, number[][]>; pooled: number[][] };
  scenarios: DemoScenario[];
  study: {
    bayCount: number;
    author: StudyMetrics;
    fixed: StudyMetrics;
    missedMinuteEpisodesPercent: number;
  };
};

type StudyMetrics = {
  samples_per_bay_day: number;
  F_seconds_per_bay_day: number;
  O_seconds_per_bay_day: number;
};

export type Decision = Observation & {
  pauseSeconds: number;
  nextTime: number;
  contextIndex: number;
  clockBin: number;
  runBin: number;
};

export type PolicyRuntime = {
  componentId: string;
  usesLocalHistory: boolean;
  component: PolicyComponent;
  decide: (observation: Readonly<Observation>) => Decision;
};

export type ReplayMetrics = {
  calls: number;
  falseFreeSeconds: number;
  falseOccupiedSeconds: number;
};
