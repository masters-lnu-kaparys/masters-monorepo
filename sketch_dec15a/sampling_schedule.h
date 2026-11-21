#pragma once

#include <stdint.h>
#include "occupancy_state.h"

constexpr uint32_t SAMPLING_ALLOCATION_SEED = 20261025;
constexpr uint16_t SAMPLING_RETRY_SECONDS = 5;

// Frozen pooled_fallback tables from frontend/public/data/sampling-demo.json.
// Each group of six entries covers one part of the day, for free then occupied.
constexpr uint16_t SAMPLING_PAUSES[3][48] = {
  { // F2/O2
    60, 60, 72, 120, 240, 300,
    30, 30, 45, 60, 75, 120,
    30, 30, 45, 60, 75, 120,
    30, 30, 45, 75, 120, 180,
    30, 30, 45, 60, 120, 240,
    30, 30, 45, 75, 90, 120,
    30, 30, 45, 72, 72, 120,
    30, 30, 60, 90, 90, 120,
  },
  { // F2/O4
    60, 60, 72, 120, 240, 300,
    30, 30, 45, 60, 75, 120,
    30, 30, 45, 60, 75, 120,
    30, 30, 45, 75, 120, 180,
    15, 15, 30, 45, 75, 180,
    15, 30, 30, 45, 60, 90,
    15, 30, 30, 45, 45, 90,
    15, 30, 45, 60, 72, 90,
  },
  { // F4/O4
    30, 45, 45, 75, 120, 240,
    15, 30, 30, 45, 45, 75,
    15, 15, 30, 45, 60, 90,
    15, 30, 30, 45, 75, 120,
    15, 15, 30, 45, 75, 180,
    15, 30, 30, 45, 60, 90,
    15, 30, 30, 45, 45, 90,
    15, 30, 45, 60, 72, 90,
  },
};

inline uint8_t samplingTableFromDigest(const uint8_t* digest) {
  uint64_t prefix = 0;
  for (uint8_t i = 0; i < 8; ++i) {
    prefix |= static_cast<uint64_t>(digest[i]) << (8 * i);
  }

  const double position = static_cast<double>(prefix) / 18446744073709551616.0;
  constexpr double firstWeight = 0.29406679572196653;
  constexpr double secondWeight = 0.07746827866892442;
  if (position < firstWeight) return 0;
  if (position < firstWeight + secondWeight) return 1;
  return 2;
}

inline uint8_t samplingContext(OccupancyState state, uint8_t localHour, uint64_t sameStateSeconds) {
  constexpr uint16_t runBoundaries[] = {60, 300, 900, 3600, 14400};
  uint8_t runBin = 0;
  for (const auto boundary : runBoundaries) {
    if (sameStateSeconds < boundary) break;
    ++runBin;
  }
  const uint8_t stateIndex = state == OccupancyState::Occupied ? 1 : 0;
  const uint8_t clockBin = localHour / 6;
  return (stateIndex * 4 + clockBin) * 6 + runBin;
}

class SamplingSchedule {
 public:
  void selectTable(const uint8_t* digest) {
    table_ = samplingTableFromDigest(digest);
  }

  bool isDue(uint64_t nowMs) const {
    return nowMs >= nextMeasurementMs_;
  }

  void retry(uint64_t nowMs) {
    nextMeasurementMs_ = nowMs + SAMPLING_RETRY_SECONDS * 1000ULL;
  }

  void resetHistory(uint64_t nowMs) {
    observedState_ = OccupancyState::Unknown;
    retry(nowMs);
  }

  uint16_t observe(OccupancyState state, uint8_t localHour, uint64_t nowMs) {
    if (state == OccupancyState::Unknown) {
      retry(nowMs);
      return SAMPLING_RETRY_SECONDS;
    }

    if (state != observedState_) {
      observedState_ = state;
      runStartMs_ = nowMs;
    }

    const auto context = samplingContext(state, localHour, (nowMs - runStartMs_) / 1000);
    const uint16_t pause = SAMPLING_PAUSES[table_][context];
    nextMeasurementMs_ = nowMs + pause * 1000ULL;
    return pause;
  }

 private:
  uint64_t nextMeasurementMs_ = SAMPLING_RETRY_SECONDS * 1000ULL;
  uint64_t runStartMs_ = 0;
  OccupancyState observedState_ = OccupancyState::Unknown;
  uint8_t table_ = 0;
};
