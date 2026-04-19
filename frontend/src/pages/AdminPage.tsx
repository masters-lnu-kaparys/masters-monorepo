import AddRoundedIcon from "@mui/icons-material/AddRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import EditRoundedIcon from "@mui/icons-material/EditRounded";
import LocalParkingRoundedIcon from "@mui/icons-material/LocalParkingRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createAdminLot,
  createAdminSpot,
  deleteAdminLot,
  deleteAdminSpot,
  fetchAdminLots,
  updateAdminLot,
  updateAdminSpot,
} from "../api/client";
import { useI18n } from "../i18n/LanguageProvider";
import type { AdminParkingLot, AdminParkingSpot, SpotSourceKind, UpsertParkingLotInput } from "../types/api";
import { SPOT_SOURCE } from "../types/api";

type LotDialogState =
  | { mode: "create"; open: true; value: UpsertParkingLotInput }
  | { mode: "edit"; open: true; lotId: number; value: UpsertParkingLotInput }
  | { open: false };

type SpotDialogState =
  | { mode: "create"; open: true; lotId: number; value: { displayName: string; sourceKind: SpotSourceKind; deviceId: string } }
  | { mode: "edit"; open: true; lotId: number; spotId: number; value: { displayName: string; sourceKind: SpotSourceKind; deviceId: string } }
  | { open: false };

type DeleteDialogState =
  | { type: "lot"; id: number; label: string }
  | { type: "spot"; id: number; label: string }
  | null;

const EMPTY_SPOT_FORM = {
  displayName: "",
  sourceKind: SPOT_SOURCE.SIMULATED,
  deviceId: "",
};

function formatLastUpdate(utc: string | null, locale: string, t: (key: string, params?: Record<string, string | number>) => string) {
  if (!utc) {
    return t("common.noDataYet");
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(utc));
}

function sourceLabel(
  sourceKind: SpotSourceKind,
  t: (key: string, params?: Record<string, string | number>) => string,
) {
  return sourceKind === SPOT_SOURCE.REAL ? t("admin.source.real") : t("admin.source.simulated");
}

function SpotSourceChip({ sourceKind }: { sourceKind: SpotSourceKind }) {
  const { t } = useI18n();

  return (
    <Chip
      size="small"
      color={sourceKind === SPOT_SOURCE.REAL ? "secondary" : "default"}
      label={sourceLabel(sourceKind, t)}
      variant={sourceKind === SPOT_SOURCE.REAL ? "filled" : "outlined"}
    />
  );
}

export function AdminPage() {
  const { t, language, locale } = useI18n();
  const [lots, setLots] = useState<AdminParkingLot[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lotDialog, setLotDialog] = useState<LotDialogState>({ open: false });
  const [spotDialog, setSpotDialog] = useState<SpotDialogState>({ open: false });
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState>(null);

  const numberFormatter = useMemo(
    () => new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }),
    [locale],
  );

  const createEmptyLotForm = useCallback<() => UpsertParkingLotInput>(() => ({
    name: "",
    city: language === "uk" ? "Львів" : "Lviv",
    address: "",
    latitude: 49.8419,
    longitude: 24.0315,
  }), [language]);

  const formatWholeNumber = useCallback(
    (value: number) => numberFormatter.format(value),
    [numberFormatter],
  );

  const selectedLot = useMemo(
    () => lots.find((lot) => lot.id === selectedLotId) ?? null,
    [lots, selectedLotId],
  );

  const loadLots = useCallback(async () => {
    setLoading(true);

    try {
      const response = await fetchAdminLots();
      setLots(response);
      setError(null);
      setSelectedLotId((previousLotId) => {
        if (response.length === 0) {
          return null;
        }

        if (previousLotId && response.some((lot) => lot.id === previousLotId)) {
          return previousLotId;
        }

        return response[0].id;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("admin.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadLots();
  }, [loadLots]);

  const handleLotDialogSubmit = useCallback(async () => {
    if (!lotDialog.open) {
      return;
    }

    setSaving(true);

    try {
      if (lotDialog.mode === "create") {
        const createdLotId = await createAdminLot(lotDialog.value);
        setSuccessMessage(t("admin.success.lotAdded"));
        await loadLots();
        setSelectedLotId(createdLotId);
      } else {
        await updateAdminLot(lotDialog.lotId, lotDialog.value);
        setSuccessMessage(t("admin.success.lotUpdated"));
        await loadLots();
        setSelectedLotId(lotDialog.lotId);
      }

      setLotDialog({ open: false });
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("admin.saveLotError"));
    } finally {
      setSaving(false);
    }
  }, [loadLots, lotDialog, t]);

  const handleSpotDialogSubmit = useCallback(async () => {
    if (!spotDialog.open) {
      return;
    }

    setSaving(true);

    try {
      const payload = {
        displayName: spotDialog.value.displayName,
        sourceKind: spotDialog.value.sourceKind,
        deviceId: spotDialog.value.deviceId.trim() ? spotDialog.value.deviceId.trim() : null,
      };

      if (spotDialog.mode === "create") {
        await createAdminSpot(spotDialog.lotId, payload);
        setSuccessMessage(t("admin.success.spotAdded"));
      } else {
        await updateAdminSpot(spotDialog.spotId, payload);
        setSuccessMessage(t("admin.success.spotUpdated"));
      }

      await loadLots();
      setSelectedLotId(spotDialog.lotId);
      setSpotDialog({ open: false });
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("admin.saveSpotError"));
    } finally {
      setSaving(false);
    }
  }, [loadLots, spotDialog, t]);

  const handleDelete = useCallback(async () => {
    if (!deleteDialog) {
      return;
    }

    setSaving(true);

    try {
      if (deleteDialog.type === "lot") {
        await deleteAdminLot(deleteDialog.id);
        setSuccessMessage(t("admin.success.lotDeleted"));
      } else {
        await deleteAdminSpot(deleteDialog.id);
        setSuccessMessage(t("admin.success.spotDeleted"));
      }

      await loadLots();
      setDeleteDialog(null);
      setError(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("admin.deleteError"));
    } finally {
      setSaving(false);
    }
  }, [deleteDialog, loadLots, t]);

  const openCreateLotDialog = () => {
    setLotDialog({
      mode: "create",
      open: true,
      value: createEmptyLotForm(),
    });
  };

  const openEditLotDialog = (lot: AdminParkingLot) => {
    setLotDialog({
      mode: "edit",
      open: true,
      lotId: lot.id,
      value: {
        name: lot.name,
        city: lot.city,
        address: lot.address,
        latitude: lot.latitude,
        longitude: lot.longitude,
      },
    });
  };

  const openCreateSpotDialog = (lotId: number) => {
    setSpotDialog({
      mode: "create",
      open: true,
      lotId,
      value: EMPTY_SPOT_FORM,
    });
  };

  const openEditSpotDialog = (lotId: number, spot: AdminParkingSpot) => {
    setSpotDialog({
      mode: "edit",
      open: true,
      lotId,
      spotId: spot.id,
      value: {
        displayName: spot.displayName,
        sourceKind: spot.sourceKind,
        deviceId: spot.deviceId,
      },
    });
  };

  return (
    <Box sx={{ px: { xs: 2, md: 4 }, py: 3.5 }}>
      <Stack spacing={3}>
        <Stack
          direction={{ xs: "column", lg: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", lg: "center" }}
          spacing={2}
        >
          <Box>
            <Typography variant="overline" sx={{ display: "block", color: "secondary.main", letterSpacing: "0.18em", fontWeight: 800 }}>
              {t("admin.overline")}
            </Typography>
            <Typography variant="h3" sx={{ mb: 1 }}>
              {t("admin.title")}
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
              {t("admin.description")}
            </Typography>
          </Box>

          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={openCreateLotDialog}>
            {t("admin.addLot")}
          </Button>
        </Stack>

        {error ? <Alert severity="error">{error}</Alert> : null}
        {successMessage ? <Alert severity="success" onClose={() => setSuccessMessage(null)}>{successMessage}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", xl: "0.95fr 1.05fr" },
            gap: 3,
          }}
        >
          <Paper sx={{ p: 2.5, borderRadius: 6, border: "1px solid rgba(17, 97, 73, 0.12)" }}>
            <Stack spacing={2}>
              <Typography variant="h5">{t("admin.lotsTitle")}</Typography>

              {loading ? (
                <Box sx={{ py: 4, textAlign: "center" }}>
                  <CircularProgress size={30} />
                </Box>
              ) : lots.length > 0 ? (
                <Stack spacing={1.25}>
                  {lots.map((lot) => {
                    const selected = lot.id === selectedLotId;

                    return (
                      <Paper
                        key={lot.id}
                        elevation={0}
                        onClick={() => setSelectedLotId(lot.id)}
                        sx={{
                          p: 2,
                          borderRadius: 4,
                          border: "1px solid",
                          borderColor: selected ? "primary.main" : "divider",
                          bgcolor: selected ? "rgba(17,97,73,0.08)" : "rgba(255,255,255,0.68)",
                          cursor: "pointer",
                        }}
                      >
                        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                          <Box>
                            <Typography fontWeight={800}>{lot.name}</Typography>
                            <Typography variant="body2" color="text.secondary">
                              {lot.address}, {lot.city}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t("admin.lotAvailability", {
                                free: formatWholeNumber(lot.freeSpots),
                                total: formatWholeNumber(lot.totalSpots),
                              })}
                            </Typography>
                          </Box>

                          <Stack direction="row" spacing={0.5}>
                            <Button size="small" variant="text" startIcon={<EditRoundedIcon />} onClick={(event) => {
                              event.stopPropagation();
                              openEditLotDialog(lot);
                            }}>
                              {t("common.edit")}
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              startIcon={<DeleteOutlineRoundedIcon />}
                              onClick={(event) => {
                                event.stopPropagation();
                                setDeleteDialog({ type: "lot", id: lot.id, label: lot.name });
                              }}
                            >
                              {t("common.delete")}
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    );
                  })}
                </Stack>
              ) : (
                <Alert severity="info">{t("admin.lotsEmpty")}</Alert>
              )}
            </Stack>
          </Paper>

          <Paper sx={{ p: 2.5, borderRadius: 6, border: "1px solid rgba(17, 97, 73, 0.12)" }}>
            {selectedLot ? (
              <Stack spacing={2.5}>
                <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                  <Box>
                    <Typography variant="overline" sx={{ display: "block", color: "secondary.main", fontWeight: 800, letterSpacing: "0.16em" }}>
                      {t("admin.selectedLot.overline")}
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 0.5 }}>
                      {selectedLot.name}
                    </Typography>
                    <Typography color="text.secondary">
                      {selectedLot.address}, {selectedLot.city}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("common.coordinates", {
                        latitude: selectedLot.latitude.toFixed(5),
                        longitude: selectedLot.longitude.toFixed(5),
                      })}
                    </Typography>
                  </Box>

                  <Button variant="outlined" startIcon={<AddRoundedIcon />} onClick={() => openCreateSpotDialog(selectedLot.id)}>
                    {t("admin.addSpot")}
                  </Button>
                </Stack>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", lg: "repeat(3, minmax(0, 1fr))" },
                    gap: 1.5,
                  }}
                >
                  <Paper elevation={0} sx={{ p: 2, borderRadius: 4, bgcolor: "rgba(255,255,255,0.68)", border: "1px solid rgba(17, 97, 73, 0.10)" }}>
                    <Typography variant="overline" color="text.secondary">{t("common.spots")}</Typography>
                    <Typography variant="h4" fontWeight={800}>{formatWholeNumber(selectedLot.totalSpots)}</Typography>
                  </Paper>
                  <Paper elevation={0} sx={{ p: 2, borderRadius: 4, bgcolor: "rgba(255,255,255,0.68)", border: "1px solid rgba(17, 97, 73, 0.10)" }}>
                    <Typography variant="overline" color="text.secondary">{t("common.freeSpots")}</Typography>
                    <Typography variant="h4" fontWeight={800}>{formatWholeNumber(selectedLot.freeSpots)}</Typography>
                  </Paper>
                  <Paper elevation={0} sx={{ p: 2, borderRadius: 4, bgcolor: "rgba(255,255,255,0.68)", border: "1px solid rgba(17, 97, 73, 0.10)" }}>
                    <Typography variant="overline" color="text.secondary">{t("common.occupiedSpots")}</Typography>
                    <Typography variant="h4" fontWeight={800}>{formatWholeNumber(selectedLot.occupiedSpots)}</Typography>
                  </Paper>
                </Box>

                <Divider />

                <Stack spacing={1.25}>
                  <Typography variant="h5">{t("common.spots")}</Typography>

                  {selectedLot.spots.length > 0 ? (
                    <Stack spacing={1}>
                      {selectedLot.spots.map((spot) => (
                        <Paper
                          key={spot.id}
                          elevation={0}
                          sx={{
                            p: 1.6,
                            borderRadius: 4,
                            border: "1px solid rgba(17, 97, 73, 0.10)",
                            bgcolor: "rgba(255,255,255,0.72)",
                          }}
                        >
                          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                            <Box>
                              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                                <Typography fontWeight={800}>{spot.displayName}</Typography>
                                <SpotSourceChip sourceKind={spot.sourceKind} />
                                <Chip
                                  size="small"
                                  color={spot.occupied ? "warning" : "success"}
                                  label={spot.occupied ? t("monitoring.status.occupied") : t("monitoring.status.free")}
                                />
                              </Stack>
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                                {t("common.deviceId")}: {spot.deviceId}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {t("common.lastMeasurement")}: {spot.distanceCm !== null ? t("common.distanceCm", { value: formatWholeNumber(spot.distanceCm) }) : t("common.noDataYet")}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                                {t("common.updatedAt")}: {formatLastUpdate(spot.lastTelemetryAtUtc, locale, t)}
                              </Typography>
                            </Box>

                            <Stack direction="row" spacing={1} alignItems="flex-start">
                              <Button size="small" startIcon={<EditRoundedIcon />} onClick={() => openEditSpotDialog(selectedLot.id, spot)}>
                                {t("common.edit")}
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                startIcon={<DeleteOutlineRoundedIcon />}
                                onClick={() => setDeleteDialog({ type: "spot", id: spot.id, label: spot.displayName })}
                              >
                                {t("common.delete")}
                              </Button>
                            </Stack>
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  ) : (
                    <Alert severity="info">{t("admin.spotsEmpty")}</Alert>
                  )}
                </Stack>
              </Stack>
            ) : (
              <Stack spacing={1.5} sx={{ minHeight: 420, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
                <LocalParkingRoundedIcon sx={{ fontSize: 44, color: "text.disabled" }} />
                <Typography variant="h5">{t("admin.selectLotTitle")}</Typography>
                <Typography color="text.secondary" sx={{ maxWidth: 420 }}>
                  {t("admin.selectLotDescription")}
                </Typography>
              </Stack>
            )}
          </Paper>
        </Box>
      </Stack>

      <Dialog open={lotDialog.open} onClose={() => !saving && setLotDialog({ open: false })} fullWidth maxWidth="sm">
        <DialogTitle>{lotDialog.open && lotDialog.mode === "create" ? t("admin.newLot") : t("admin.editLot")}</DialogTitle>
        <DialogContent>
          {lotDialog.open ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label={t("admin.field.name")}
                value={lotDialog.value.name}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, name: event.target.value } } : current)}
                fullWidth
              />
              <TextField
                label={t("admin.field.city")}
                value={lotDialog.value.city}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, city: event.target.value } } : current)}
                fullWidth
              />
              <TextField
                label={t("admin.field.address")}
                value={lotDialog.value.address}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, address: event.target.value } } : current)}
                fullWidth
              />
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  label={t("admin.field.latitude")}
                  type="number"
                  value={lotDialog.value.latitude}
                  onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, latitude: Number(event.target.value) } } : current)}
                  fullWidth
                />
                <TextField
                  label={t("admin.field.longitude")}
                  type="number"
                  value={lotDialog.value.longitude}
                  onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, longitude: Number(event.target.value) } } : current)}
                  fullWidth
                />
              </Stack>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLotDialog({ open: false })} disabled={saving}>{t("common.cancel")}</Button>
          <Button variant="contained" onClick={() => void handleLotDialogSubmit()} disabled={saving}>
            {lotDialog.open && lotDialog.mode === "create" ? t("common.create") : t("common.save")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={spotDialog.open} onClose={() => !saving && setSpotDialog({ open: false })} fullWidth maxWidth="sm">
        <DialogTitle>{spotDialog.open && spotDialog.mode === "create" ? t("admin.newSpot") : t("admin.editSpot")}</DialogTitle>
        <DialogContent>
          {spotDialog.open ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label={t("admin.field.spotName")}
                value={spotDialog.value.displayName}
                onChange={(event) => setSpotDialog((current) => current.open ? { ...current, value: { ...current.value, displayName: event.target.value } } : current)}
                fullWidth
              />
              <FormControl fullWidth>
                <InputLabel id="spot-source-label">{t("admin.field.sourceKind")}</InputLabel>
                <Select
                  labelId="spot-source-label"
                  label={t("admin.field.sourceKind")}
                  value={spotDialog.value.sourceKind}
                  onChange={(event) => setSpotDialog((current) => current.open ? {
                    ...current,
                    value: {
                      ...current.value,
                      sourceKind: Number(event.target.value) as SpotSourceKind,
                    },
                  } : current)}
                >
                  <MenuItem value={SPOT_SOURCE.REAL}>{t("admin.source.real")}</MenuItem>
                  <MenuItem value={SPOT_SOURCE.SIMULATED}>{t("admin.source.simulated")}</MenuItem>
                </Select>
                <FormHelperText>{t("admin.field.sourceKindHelp")}</FormHelperText>
              </FormControl>
              <TextField
                label={t("admin.field.deviceId")}
                value={spotDialog.value.deviceId}
                onChange={(event) => setSpotDialog((current) => current.open ? { ...current, value: { ...current.value, deviceId: event.target.value } } : current)}
                placeholder={spotDialog.value.sourceKind === SPOT_SOURCE.SIMULATED ? t("admin.field.deviceId.autoPlaceholder") : t("admin.field.deviceId.realPlaceholder")}
                fullWidth
              />
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSpotDialog({ open: false })} disabled={saving}>{t("common.cancel")}</Button>
          <Button variant="contained" onClick={() => void handleSpotDialogSubmit()} disabled={saving}>
            {spotDialog.open && spotDialog.mode === "create" ? t("common.create") : t("common.save")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialog !== null} onClose={() => !saving && setDeleteDialog(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t("admin.deleteConfirmTitle")}</DialogTitle>
        <DialogContent>
          <Stack spacing={1.25} sx={{ mt: 1 }}>
            <Typography>
              {deleteDialog?.type === "lot"
                ? t("admin.deleteConfirmLot", { label: deleteDialog.label })
                : t("admin.deleteConfirmSpot", { label: deleteDialog?.label ?? "" })}
            </Typography>
            <Alert severity="warning">{t("admin.deleteWarning")}</Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(null)} disabled={saving}>{t("common.cancel")}</Button>
          <Button color="error" variant="contained" onClick={() => void handleDelete()} disabled={saving}>
            {t("common.delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
