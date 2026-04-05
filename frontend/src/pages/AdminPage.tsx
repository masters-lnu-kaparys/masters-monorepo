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

const EMPTY_LOT_FORM: UpsertParkingLotInput = {
  name: "",
  city: "Львів",
  address: "",
  latitude: 49.8419,
  longitude: 24.0315,
};

const EMPTY_SPOT_FORM = {
  displayName: "",
  sourceKind: SPOT_SOURCE.SIMULATED,
  deviceId: "",
};

function formatLastUpdate(utc: string | null) {
  return utc ? new Date(utc).toLocaleString() : "ще немає даних";
}

function sourceLabel(sourceKind: SpotSourceKind) {
  return sourceKind === SPOT_SOURCE.REAL ? "Real" : "Simulated";
}

function SpotSourceChip({ sourceKind }: { sourceKind: SpotSourceKind }) {
  return (
    <Chip
      size="small"
      color={sourceKind === SPOT_SOURCE.REAL ? "secondary" : "default"}
      label={sourceLabel(sourceKind)}
      variant={sourceKind === SPOT_SOURCE.REAL ? "filled" : "outlined"}
    />
  );
}

export function AdminPage() {
  const [lots, setLots] = useState<AdminParkingLot[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lotDialog, setLotDialog] = useState<LotDialogState>({ open: false });
  const [spotDialog, setSpotDialog] = useState<SpotDialogState>({ open: false });
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState>(null);

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
      setError(loadError instanceof Error ? loadError.message : "Не вдалося завантажити список парковок.");
    } finally {
      setLoading(false);
    }
  }, []);

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
        setSuccessMessage("Парковку додано.");
        await loadLots();
        setSelectedLotId(createdLotId);
      } else {
        await updateAdminLot(lotDialog.lotId, lotDialog.value);
        setSuccessMessage("Дані парковки оновлено.");
        await loadLots();
        setSelectedLotId(lotDialog.lotId);
      }

      setLotDialog({ open: false });
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Не вдалося зберегти парковку.");
    } finally {
      setSaving(false);
    }
  }, [loadLots, lotDialog]);

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
        setSuccessMessage("Місце додано.");
      } else {
        await updateAdminSpot(spotDialog.spotId, payload);
        setSuccessMessage("Місце оновлено.");
      }

      await loadLots();
      setSelectedLotId(spotDialog.lotId);
      setSpotDialog({ open: false });
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Не вдалося зберегти місце.");
    } finally {
      setSaving(false);
    }
  }, [loadLots, spotDialog]);

  const handleDelete = useCallback(async () => {
    if (!deleteDialog) {
      return;
    }

    setSaving(true);

    try {
      if (deleteDialog.type === "lot") {
        await deleteAdminLot(deleteDialog.id);
        setSuccessMessage("Парковку видалено.");
      } else {
        await deleteAdminSpot(deleteDialog.id);
        setSuccessMessage("Місце видалено.");
      }

      await loadLots();
      setDeleteDialog(null);
      setError(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Не вдалося виконати видалення.");
    } finally {
      setSaving(false);
    }
  }, [deleteDialog, loadLots]);

  const openCreateLotDialog = () => {
    setLotDialog({
      mode: "create",
      open: true,
      value: EMPTY_LOT_FORM,
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
              ADMIN PANEL
            </Typography>
            <Typography variant="h3" sx={{ mb: 1 }}>
              Керування парковками та місцями
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
              Тут адміністратор створює міські парковки, підтримує їх координати на карті та прив&apos;язує реальні або симульовані місця.
            </Typography>
          </Box>

          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={openCreateLotDialog}>
            Додати парковку
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
              <Typography variant="h5">Парковки</Typography>

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
                              {lot.freeSpots} вільно з {lot.totalSpots} місць
                            </Typography>
                          </Box>

                          <Stack direction="row" spacing={0.5}>
                            <Button size="small" variant="text" startIcon={<EditRoundedIcon />} onClick={(event) => {
                              event.stopPropagation();
                              openEditLotDialog(lot);
                            }}>
                              Змінити
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
                              Видалити
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    );
                  })}
                </Stack>
              ) : (
                <Alert severity="info">Ще немає жодної парковки. Створи першу через кнопку зверху.</Alert>
              )}
            </Stack>
          </Paper>

          <Paper sx={{ p: 2.5, borderRadius: 6, border: "1px solid rgba(17, 97, 73, 0.12)" }}>
            {selectedLot ? (
              <Stack spacing={2.5}>
                <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                  <Box>
                    <Typography variant="overline" sx={{ display: "block", color: "secondary.main", fontWeight: 800, letterSpacing: "0.16em" }}>
                      ОБРАНА ПАРКОВКА
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 0.5 }}>
                      {selectedLot.name}
                    </Typography>
                    <Typography color="text.secondary">
                      {selectedLot.address}, {selectedLot.city}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Координати: {selectedLot.latitude.toFixed(5)}, {selectedLot.longitude.toFixed(5)}
                    </Typography>
                  </Box>

                  <Button variant="outlined" startIcon={<AddRoundedIcon />} onClick={() => openCreateSpotDialog(selectedLot.id)}>
                    Додати місце
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
                    <Typography variant="overline" color="text.secondary">Місць</Typography>
                    <Typography variant="h4" fontWeight={800}>{selectedLot.totalSpots}</Typography>
                  </Paper>
                  <Paper elevation={0} sx={{ p: 2, borderRadius: 4, bgcolor: "rgba(255,255,255,0.68)", border: "1px solid rgba(17, 97, 73, 0.10)" }}>
                    <Typography variant="overline" color="text.secondary">Вільно</Typography>
                    <Typography variant="h4" fontWeight={800}>{selectedLot.freeSpots}</Typography>
                  </Paper>
                  <Paper elevation={0} sx={{ p: 2, borderRadius: 4, bgcolor: "rgba(255,255,255,0.68)", border: "1px solid rgba(17, 97, 73, 0.10)" }}>
                    <Typography variant="overline" color="text.secondary">Зайнято</Typography>
                    <Typography variant="h4" fontWeight={800}>{selectedLot.occupiedSpots}</Typography>
                  </Paper>
                </Box>

                <Divider />

                <Stack spacing={1.25}>
                  <Typography variant="h5">Місця</Typography>

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
                                  label={spot.occupied ? "Зайнято" : "Вільно"}
                                />
                              </Stack>
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                                deviceId: {spot.deviceId}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Останнє вимірювання: {spot.distanceCm !== null ? `${spot.distanceCm.toFixed(0)} см` : "ще немає даних"}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                                Оновлено: {formatLastUpdate(spot.lastTelemetryAtUtc)}
                              </Typography>
                            </Box>

                            <Stack direction="row" spacing={1} alignItems="flex-start">
                              <Button size="small" startIcon={<EditRoundedIcon />} onClick={() => openEditSpotDialog(selectedLot.id, spot)}>
                                Змінити
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                startIcon={<DeleteOutlineRoundedIcon />}
                                onClick={() => setDeleteDialog({ type: "spot", id: spot.id, label: spot.displayName })}
                              >
                                Видалити
                              </Button>
                            </Stack>
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  ) : (
                    <Alert severity="info">На цій парковці поки немає місць. Додай перше місце і воно одразу потрапить на карту та в realtime.</Alert>
                  )}
                </Stack>
              </Stack>
            ) : (
              <Stack spacing={1.5} sx={{ minHeight: 420, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
                <LocalParkingRoundedIcon sx={{ fontSize: 44, color: "text.disabled" }} />
                <Typography variant="h5">Оберіть парковку</Typography>
                <Typography color="text.secondary" sx={{ maxWidth: 420 }}>
                  Після вибору тут з&apos;являться координати, список місць та дії для редагування.
                </Typography>
              </Stack>
            )}
          </Paper>
        </Box>
      </Stack>

      <Dialog open={lotDialog.open} onClose={() => !saving && setLotDialog({ open: false })} fullWidth maxWidth="sm">
        <DialogTitle>{lotDialog.open && lotDialog.mode === "create" ? "Нова парковка" : "Редагування парковки"}</DialogTitle>
        <DialogContent>
          {lotDialog.open ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Назва"
                value={lotDialog.value.name}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, name: event.target.value } } : current)}
                fullWidth
              />
              <TextField
                label="Місто"
                value={lotDialog.value.city}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, city: event.target.value } } : current)}
                fullWidth
              />
              <TextField
                label="Адреса"
                value={lotDialog.value.address}
                onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, address: event.target.value } } : current)}
                fullWidth
              />
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  label="Latitude"
                  type="number"
                  value={lotDialog.value.latitude}
                  onChange={(event) => setLotDialog((current) => current.open ? { ...current, value: { ...current.value, latitude: Number(event.target.value) } } : current)}
                  fullWidth
                />
                <TextField
                  label="Longitude"
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
          <Button onClick={() => setLotDialog({ open: false })} disabled={saving}>Скасувати</Button>
          <Button variant="contained" onClick={() => void handleLotDialogSubmit()} disabled={saving}>
            {lotDialog.open && lotDialog.mode === "create" ? "Створити" : "Зберегти"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={spotDialog.open} onClose={() => !saving && setSpotDialog({ open: false })} fullWidth maxWidth="sm">
        <DialogTitle>{spotDialog.open && spotDialog.mode === "create" ? "Нове місце" : "Редагування місця"}</DialogTitle>
        <DialogContent>
          {spotDialog.open ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Назва місця"
                value={spotDialog.value.displayName}
                onChange={(event) => setSpotDialog((current) => current.open ? { ...current, value: { ...current.value, displayName: event.target.value } } : current)}
                fullWidth
              />
              <FormControl fullWidth>
                <InputLabel id="spot-source-label">Тип джерела</InputLabel>
                <Select
                  labelId="spot-source-label"
                  label="Тип джерела"
                  value={spotDialog.value.sourceKind}
                  onChange={(event) => setSpotDialog((current) => current.open ? {
                    ...current,
                    value: {
                      ...current.value,
                      sourceKind: Number(event.target.value) as SpotSourceKind,
                    },
                  } : current)}
                >
                  <MenuItem value={SPOT_SOURCE.REAL}>Real</MenuItem>
                  <MenuItem value={SPOT_SOURCE.SIMULATED}>Simulated</MenuItem>
                </Select>
                <FormHelperText>
                  Real очікує фізичний device ID, а Simulated може згенерувати його автоматично.
                </FormHelperText>
              </FormControl>
              <TextField
                label="Device ID"
                value={spotDialog.value.deviceId}
                onChange={(event) => setSpotDialog((current) => current.open ? { ...current, value: { ...current.value, deviceId: event.target.value } } : current)}
                placeholder={spotDialog.value.sourceKind === SPOT_SOURCE.SIMULATED ? "Залиши порожнім для автогенерації" : "Наприклад ps-lviv-001"}
                fullWidth
              />
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSpotDialog({ open: false })} disabled={saving}>Скасувати</Button>
          <Button variant="contained" onClick={() => void handleSpotDialogSubmit()} disabled={saving}>
            {spotDialog.open && spotDialog.mode === "create" ? "Створити" : "Зберегти"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialog !== null} onClose={() => !saving && setDeleteDialog(null)} fullWidth maxWidth="xs">
        <DialogTitle>Підтвердь видалення</DialogTitle>
        <DialogContent>
          <Stack spacing={1.25} sx={{ mt: 1 }}>
            <Typography>
              {deleteDialog?.type === "lot"
                ? `Видалити парковку "${deleteDialog.label}" разом із місцями та історією телеметрії?`
                : `Видалити місце "${deleteDialog?.label}" разом із його історією телеметрії?`}
            </Typography>
            <Alert severity="warning">Цю дію не можна буде скасувати.</Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(null)} disabled={saving}>Скасувати</Button>
          <Button color="error" variant="contained" onClick={() => void handleDelete()} disabled={saving}>
            Видалити
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
