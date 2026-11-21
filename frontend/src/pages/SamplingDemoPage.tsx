import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import DownloadRoundedIcon from "@mui/icons-material/DownloadRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import PauseRoundedIcon from "@mui/icons-material/PauseRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import ReplayRoundedIcon from "@mui/icons-material/ReplayRounded";
import SkipNextRoundedIcon from "@mui/icons-material/SkipNextRounded";
import { Accordion, AccordionDetails, AccordionSummary, Alert, AppBar, Box, Button, Chip,
  CircularProgress, Container, Divider, MenuItem, Paper, Slider, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Toolbar, Typography } from "@mui/material";
import { APP_ROUTES } from "../app/routes";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useI18n } from "../i18n/context";
import { createPolicyRuntime } from "../sampling/policy";
import { actionComparisons, buildReplay, formatSourceTime, latestDecision, replayMetrics, validateScenario } from "../sampling/replay";
import { SamplingTimeline } from "../sampling/SamplingTimeline";
import type { Decision, DemoData, DemoScenario, PolicyRuntime } from "../sampling/types";

const panel = { p: { xs: 2, md: 3 }, border: "1px solid rgba(17,97,73,0.12)", borderRadius: "16px" };

function StatCard({ title, value, comparison }: { title: string; value: string; comparison: string }) {
  return <Paper role="group" aria-label={title} elevation={0} sx={{ ...panel, flex: 1, minWidth: 0 }}>
    <Typography color="text.secondary" variant="body2" sx={{ minHeight: { md: 40 } }}>{title}</Typography>
    <Typography sx={{ fontSize: "2rem", fontWeight: 800, color: "primary.dark", my: 0.5 }}>{value}</Typography>
    <Typography variant="body2" color="text.secondary">{comparison}</Typography>
  </Paper>;
}

function ScenarioReplay({ data, scenario, runtime }: { data: DemoData; scenario: DemoScenario; runtime: PolicyRuntime }) {
  const { t, locale } = useI18n();
  const [cursor, setCursor] = useState(scenario.startTime);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(30);
  const replay = useMemo(() => buildReplay(scenario, runtime), [scenario, runtime]);
  const running = playing && cursor < scenario.endTime;
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setCursor(time => Math.min(scenario.endTime, time + speed / 5)), 200);
    return () => window.clearInterval(timer);
  }, [running, speed, scenario.endTime]);
  const author = replayMetrics(scenario, replay.author, cursor);
  const fixed = replayMetrics(scenario, replay.fixed, cursor);
  const decision = latestDecision(replay.author, cursor);
  const comparisons = actionComparisons(data, scenario, runtime, decision);
  const log = replay.author.filter(d => d.time <= cursor);
  const number = (value: number, digits = 0) => value.toLocaleString(locale, { maximumFractionDigits: digits });
  const seconds = (value: number) => t("sampling.seconds", { value: number(value, 1) });
  const occupancy = (state: number) => t(state === 1 ? "sampling.occupied" : "sampling.free");
  const reset = () => { setPlaying(false); setCursor(scenario.startTime); };
  const next = () => {
    setPlaying(false);
    setCursor(replay.author.find(d => d.time > cursor)?.time ?? scenario.endTime);
  };
  const togglePlayback = () => {
    if (cursor >= scenario.endTime) { setCursor(scenario.startTime); setPlaying(true); }
    else setPlaying(!playing);
  };
  const exportLog = () => {
    const rows: (string | number)[][] = [[t("sampling.csvBay"), t("sampling.csvMethod"), t("sampling.logTime"),
      t("sampling.logState"), t("sampling.logAge"), t("sampling.logPause"), t("sampling.logNext")]];
    for (const [name, decisions] of [["author", replay.author], ["fixed", replay.fixed]] as const) {
      for (const d of decisions.filter(d => d.time >= scenario.startTime && d.time <= cursor)) {
        rows.push([scenario.bayId, t(`sampling.${name}`), formatSourceTime(d.time), occupancy(d.state),
          d.time - d.observedRunStart, d.pauseSeconds, formatSourceTime(d.nextTime)]);
      }
    }
    const csv = "\uFEFF" + rows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `measurements-${scenario.bayId}-${scenario.dateLocal}.csv`; anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const visibleLog: Decision[] = [...log].reverse().slice(0, 8);

  return <Stack spacing={2.5}>
    <Paper elevation={0} sx={panel}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
        <Button variant="contained" onClick={togglePlayback} startIcon={running ? <PauseRoundedIcon /> : <PlayArrowRoundedIcon />}>
          {t(running ? "sampling.pause" : "sampling.play")}
        </Button>
        <Button variant="outlined" onClick={next} disabled={cursor >= scenario.endTime} startIcon={<SkipNextRoundedIcon />}>{t("sampling.next")}</Button>
        <Button onClick={reset} startIcon={<ReplayRoundedIcon />}>{t("sampling.restart")}</Button>
        <Box sx={{ flex: 1 }} />
        <TextField select size="small" label={t("sampling.speed")} value={speed} onChange={event => setSpeed(Number(event.target.value))} sx={{ minWidth: 120 }}>
          {[10, 30, 60].map(value => <MenuItem key={value} value={value}>{t("sampling.speedValue", { value })}</MenuItem>)}
        </TextField>
        <Typography sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 800, minWidth: 88 }}>{formatSourceTime(cursor)}</Typography>
      </Stack>
      <Slider aria-label={t("sampling.progress")} value={cursor - scenario.startTime} min={0} max={scenario.endTime - scenario.startTime}
        onChange={(_, value) => { setPlaying(false); setCursor(scenario.startTime + Number(value)); }} sx={{ mt: 2, mb: 0 }} />
      {cursor >= scenario.endTime && <Typography variant="caption" color="text.secondary">{t("sampling.finished")}</Typography>}
    </Paper>

    <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
      <StatCard title={t("sampling.calls")} value={number(author.calls)} comparison={t("sampling.fixedValue", { value: number(fixed.calls) })} />
      <StatCard title={t("sampling.falseFree")} value={seconds(author.falseFreeSeconds)} comparison={t("sampling.fixedValue", { value: seconds(fixed.falseFreeSeconds) })} />
      <StatCard title={t("sampling.falseOccupied")} value={seconds(author.falseOccupiedSeconds)} comparison={t("sampling.fixedValue", { value: seconds(fixed.falseOccupiedSeconds) })} />
    </Stack>
    <Typography variant="caption" color="text.secondary" sx={{ mt: "8px !important" }}>{t("sampling.metricsScope")}</Typography>

    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 2.1fr) minmax(290px, 1fr)" }, gap: 2.5 }}>
      <Paper elevation={0} sx={{ ...panel, minWidth: 0 }}>
        <Typography component="h2" variant="h6" sx={{ fontWeight: 800, mb: 2 }}>{t("sampling.timeline")}</Typography>
        <SamplingTimeline scenario={scenario} author={replay.author} fixed={replay.fixed} cursor={cursor} />
      </Paper>
      <Paper elevation={0} sx={{ ...panel, bgcolor: "#edf4ee" }}>
        <Stack spacing={1.75}>
          <Typography component="h2" variant="h6" sx={{ fontWeight: 800 }}>{t("sampling.decisionTitle")}</Typography>
          <Box><Chip label={occupancy(decision.state)} color={decision.state === 1 ? "warning" : "success"} size="small" />
            <Typography variant="body2" sx={{ mt: 1 }}>{t("sampling.lastAt", { time: formatSourceTime(decision.time) })}</Typography>
          </Box>
          <Divider />
          <Box><Typography variant="body2" color="text.secondary">{t("sampling.pauseLabel")}</Typography>
            <Typography sx={{ fontSize: "2.6rem", fontWeight: 800, color: "primary.dark", lineHeight: 1.2 }}>{seconds(decision.pauseSeconds)}</Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>{t("sampling.nextAt", { time: formatSourceTime(decision.nextTime) })}</Typography>
            {cursor < scenario.endTime && <Typography variant="body2" color="text.secondary">
              {t("sampling.remaining", { seconds: number(Math.max(0, Math.ceil(decision.nextTime - cursor))) })}</Typography>}
          </Box>
          <Divider />
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{t("sampling.observedRun", { seconds: number(decision.time - decision.observedRunStart) })}</Typography>
          <Typography variant="caption" color="text.secondary">{t("sampling.runExplanation")}</Typography>
          <Typography variant="body2">{t(`sampling.clock${decision.clockBin}`)}</Typography>
          <Typography variant="body2" color="text.secondary">{t(runtime.usesLocalHistory ? "sampling.localHistory" : "sampling.sharedHistory")}</Typography>
        </Stack>
      </Paper>
    </Box>

    <Accordion disableGutters elevation={0} sx={{ border: "1px solid rgba(17,97,73,0.12)", borderRadius: "12px !important", "&:before": { display: "none" } }}>
      <AccordionSummary aria-label={t("sampling.costTitle")} expandIcon={<ExpandMoreRoundedIcon />}><Typography sx={{ fontWeight: 800 }}>{t("sampling.costTitle")}</Typography></AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t("sampling.costExplanation")}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t("sampling.penalties", { free: runtime.component.lambdaF, occupied: runtime.component.lambdaO })}</Typography>
        <TableContainer><Table size="small" aria-label={t("sampling.costTitle")}>
          <TableHead><TableRow>{["costPause", "costError", "costScore"].map(key => <TableCell key={key}>{t(`sampling.${key}`)}</TableCell>)}</TableRow></TableHead>
          <TableBody>{comparisons.map(row => <TableRow key={row.pause} selected={row.selected}>
            <TableCell sx={{ fontWeight: row.selected ? 800 : 400 }}>{seconds(row.pause)}</TableCell>
            <TableCell>{number(row.expectedError, 3)}</TableCell><TableCell>{number(row.score, 5)}</TableCell>
          </TableRow>)}</TableBody>
        </Table></TableContainer>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>{t("sampling.costNote")}</Typography>
      </AccordionDetails>
    </Accordion>

    <Paper elevation={0} sx={{ ...panel, minWidth: 0 }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ mb: 2 }}>
        <Box><Typography component="h2" variant="h6" sx={{ fontWeight: 800 }}>{t("sampling.logTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">{t("sampling.logDescription")}</Typography></Box>
        <Button onClick={exportLog} startIcon={<DownloadRoundedIcon />} disabled={author.calls + fixed.calls === 0}>{t("sampling.export")}</Button>
      </Stack>
      <TableContainer><Table size="small" aria-label={t("sampling.logTitle")}>
        <TableHead><TableRow>{["logTime", "logState", "logAge", "logPause", "logNext"].map(key => <TableCell key={key} sx={{ whiteSpace: "nowrap" }}>{t(`sampling.${key}`)}</TableCell>)}</TableRow></TableHead>
        <TableBody>{visibleLog.map((d, i) => <TableRow key={d.time} selected={i === 0}>
          <TableCell sx={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>{formatSourceTime(d.time)}
            {d.time < scenario.startTime && <Typography variant="caption" color="text.secondary" display="block">{t("sampling.beforeClip")}</Typography>}</TableCell>
          <TableCell>{occupancy(d.state)}</TableCell><TableCell>{seconds(d.time - d.observedRunStart)}</TableCell>
          <TableCell sx={{ fontWeight: 800 }}>{seconds(d.pauseSeconds)}</TableCell><TableCell>{formatSourceTime(d.nextTime)}</TableCell>
        </TableRow>)}</TableBody>
      </Table></TableContainer>
    </Paper>
  </Stack>;
}

export function SamplingDemoPage() {
  const { t, locale } = useI18n();
  const [loaded, setLoaded] = useState<{ data: DemoData; runtimes: PolicyRuntime[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}data/sampling-demo.json`, { signal: controller.signal });
        if (!response.ok) throw new Error("Demo data unavailable");
        const data: DemoData = await response.json();
        if (data.schemaVersion !== 1 || !data.scenarios.length) throw new Error("Invalid demo data");
        data.scenarios.forEach(validateScenario);
        const runtimes = await Promise.all(data.scenarios.map(s => createPolicyRuntime(data.policy, s.bayId)));
        if (!controller.signal.aborted) setLoaded({ data, runtimes });
      } catch {
        if (!controller.signal.aborted) setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [attempt]);

  const data = loaded?.data;
  const selectedIndex = data ? Math.max(0, data.scenarios.findIndex(s => s.id === selectedId)) : 0;
  const scenario = data?.scenarios[selectedIndex];
  const percent = (a: number, b: number) => (100 * (1 - a / b)).toLocaleString(locale, { maximumFractionDigits: 2 }) + "%";

  return <Box sx={{ minHeight: "100vh", pb: 5 }}>
    <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: "1px solid rgba(17,97,73,0.12)", bgcolor: "rgba(253,251,247,0.92)" }}>
      <Container maxWidth="xl"><Toolbar disableGutters sx={{ gap: 2, justifyContent: "space-between", flexWrap: "wrap", py: 1 }}>
        <Typography variant="h6" sx={{ fontWeight: 800 }}>Smart Parking</Typography>
        <Stack direction="row" spacing={1} alignItems="center"><LanguageSwitcher compact />
          <Button component={RouterLink} to={APP_ROUTES.home} startIcon={<ArrowBackRoundedIcon />}>{t("sampling.back")}</Button></Stack>
      </Toolbar></Container>
    </AppBar>
    <Container component="main" maxWidth="xl" sx={{ pt: { xs: 3, md: 4 } }}>
      <Stack spacing={3}>
        <Box><Typography variant="overline" color="primary.main" sx={{ fontWeight: 800, letterSpacing: ".12em" }}>{t("sampling.badge")}</Typography>
          <Typography component="h1" variant="h3" sx={{ fontSize: { xs: "2rem", md: "2.75rem" }, mt: 0.5, mb: 1.5 }}>{t("sampling.title")}</Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 900 }}>{t("sampling.description")}</Typography></Box>
        {failed ? <Alert severity="error" action={<Button onClick={() => { setFailed(false); setAttempt(value => value + 1); }}>{t("sampling.retry")}</Button>}>{t("sampling.loadError")}</Alert>
          : !loaded || !data || !scenario ? <Stack direction="row" alignItems="center" spacing={2}><CircularProgress size={24} /><Typography>{t("sampling.loading")}</Typography></Stack>
          : <>
            <Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems={{ sm: "center" }}>
              <TextField select label={t("sampling.spot")} value={scenario.id} onChange={event => setSelectedId(event.target.value)} size="small" sx={{ minWidth: 200 }}>
                {data.scenarios.map(s => <MenuItem key={s.id} value={s.id}>{t("sampling.spotOption", { bay: s.bayId })}</MenuItem>)}
              </TextField>
              <Typography variant="body2" color="text.secondary">{t("sampling.recordDate", { date: new Date(scenario.startTime * 1000).toLocaleDateString(locale, { timeZone: "UTC" }) })}</Typography>
            </Stack>
            <ScenarioReplay key={scenario.id} data={data} scenario={scenario} runtime={loaded.runtimes[selectedIndex]} />
            <Accordion disableGutters elevation={0} sx={{ ...panel, p: "0 !important", "&:before": { display: "none" } }}>
              <AccordionSummary aria-label={t("sampling.studyTitle")} expandIcon={<ExpandMoreRoundedIcon />}><Typography sx={{ fontWeight: 800 }}>{t("sampling.studyTitle")}</Typography></AccordionSummary>
              <AccordionDetails><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t("sampling.studyScope", { bays: data.study.bayCount })}</Typography>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  {[
                    ["studyCalls", data.study.author.samples_per_bay_day, data.study.fixed.samples_per_bay_day],
                    ["studyFree", data.study.author.F_seconds_per_bay_day, data.study.fixed.F_seconds_per_bay_day],
                    ["studyOccupied", data.study.author.O_seconds_per_bay_day, data.study.fixed.O_seconds_per_bay_day],
                  ].map(([label, a, b]) => <Box key={label} sx={{ flex: 1 }}><Typography variant="h4" color="primary.main" sx={{ fontWeight: 800 }}>{percent(Number(a), Number(b))}</Typography>
                    <Typography variant="body2">{t(`sampling.${label}`)}</Typography></Box>)}
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>{t("sampling.studyTradeoff", { percent: data.study.missedMinuteEpisodesPercent.toLocaleString(locale, { maximumFractionDigits: 3 }) })}</Typography>
              </AccordionDetails>
            </Accordion>
            <Box><Typography variant="body2" component="a" href={data.source.url} target="_blank" rel="noreferrer" color="primary.main">{t("sampling.source")}</Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>{t("sampling.sourceNote")}</Typography></Box>
          </>}
      </Stack>
    </Container>
  </Box>;
}
