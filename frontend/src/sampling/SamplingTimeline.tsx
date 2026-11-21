import { Box, Stack, Typography } from "@mui/material";
import { useI18n } from "../i18n/context";
import { errorIntervals, formatSourceTime } from "./replay";
import type { Decision, DemoScenario, Segment } from "./types";

const LEFT = 205;
const RIGHT = 1055;
const WIDTH = 1080;

export function SamplingTimeline({ scenario, author, fixed, cursor }: {
  scenario: DemoScenario; author: Decision[]; fixed: Decision[]; cursor: number;
}) {
  const { t } = useI18n();
  const x = (time: number) => LEFT + (time - scenario.startTime) / (scenario.endTime - scenario.startTime) * (RIGHT - LEFT);
  const y = (state: number, row: number) => 38 + row * 84 + (state === 1 ? 0 : 35);
  const spans = (decisions: Decision[]): Segment[] => decisions.flatMap((d, i) => {
    const start = Math.max(d.time, scenario.startTime);
    const end = Math.min(cursor, decisions[i + 1]?.time ?? scenario.endTime);
    return start < end ? [{ start, end, state: d.state }] : [];
  });
  const rows = [
    { label: t("sampling.sourceState"), color: "#64748b", segments: scenario.segments, decisions: [] as Decision[] },
    { label: t("sampling.fixed"), color: "#d97706", segments: spans(fixed), decisions: fixed },
    { label: t("sampling.author"), color: "#116149", segments: spans(author), decisions: author },
  ];
  const line = (segments: Segment[], row: number) => segments.map((s, i) =>
    `${i === 0 ? "M" : "L"}${x(s.start)},${y(s.state, row)} H${x(s.end)}`).join(" ");

  return (
    <Stack spacing={1.5}>
      <Box sx={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${WIDTH} 305`} style={{ display: "block", width: "100%", minWidth: 660 }}
          role="img" aria-label={t("sampling.chartAria")}>
          <rect x={x(cursor)} y={18} width={Math.max(0, RIGHT - x(cursor))} height={240} fill="#f0ede6" opacity={0.65} />
          {rows.map((row, index) => (
            <g key={row.label}>
              <text x={2} y={y(1, index) + 21} fontSize={15} fontWeight={700} fill="#334155">{row.label}</text>
              {[0, 1].map(state => <g key={state}>
                <text x={LEFT - 12} y={y(state, index) + 5} textAnchor="end" fontSize={12} fill="#64748b">
                  {t(state === 1 ? "sampling.occupied" : "sampling.free")}
                </text>
                <line x1={LEFT} x2={RIGHT} y1={y(state, index)} y2={y(state, index)} stroke="#e2e8e5" />
              </g>)}
              {index > 0 && errorIntervals(scenario, row.decisions, cursor).map((s, j) =>
                <rect key={j} x={x(s.start)} y={y(1, index) - 8} width={x(s.end) - x(s.start)} height={51} fill="#f2ce9b" opacity={0.55} />)}
              <path d={line(row.segments, index)} fill="none" stroke={row.color} strokeWidth={2.5} strokeLinejoin="round" />
              {row.decisions.filter(d => d.time >= scenario.startTime && d.time <= cursor).map(d =>
                <circle key={d.time} cx={x(d.time)} cy={y(d.state, index)} r={4} fill={row.color} stroke="#fffdf7" strokeWidth={1} />)}
            </g>
          ))}
          <line x1={x(cursor)} x2={x(cursor)} y1={12} y2={260} stroke="#1f2937" strokeDasharray="4 4" />
          <text x={Math.max(LEFT + 44, Math.min(RIGHT - 44, x(cursor)))} y={294} textAnchor="middle" fontSize={13} fontWeight={800} fill="#1f2937">
            {formatSourceTime(cursor)}
          </text>
          {[0, 1, 2, 3, 4].map(i => {
            const time = scenario.startTime + i * (scenario.endTime - scenario.startTime) / 4;
            return <text key={i} x={x(time)} y={277} textAnchor="middle" fontSize={12} fill="#64748b">{formatSourceTime(time).slice(0, 5)}</text>;
          })}
        </svg>
      </Box>
      <Stack direction="row" useFlexGap flexWrap="wrap" gap={2}>
        {["legendDots", "legendError", "legendCursor"].map(key =>
          <Typography variant="caption" key={key} color="text.secondary">{t(`sampling.${key}`)}</Typography>)}
      </Stack>
      <Typography variant="body2" color="text.secondary">{t("sampling.causality")}</Typography>
    </Stack>
  );
}
