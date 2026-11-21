#pragma once

enum class OccupancyState { Unknown, Free, Occupied };

constexpr OccupancyState nextOccupancyState(
  float cm, float occupiedBelowCm, float freeAboveCm, OccupancyState previous) {
  return cm < occupiedBelowCm ? OccupancyState::Occupied
       : cm > freeAboveCm ? OccupancyState::Free
       : previous;
}

#ifdef OCCUPANCY_STATE_TEST
static_assert(nextOccupancyState(48.0f, 40.0f, 55.0f, OccupancyState::Unknown) == OccupancyState::Unknown,
              "A first measurement between thresholds leaves the state unknown");
static_assert(nextOccupancyState(40.0f, 40.0f, 55.0f, OccupancyState::Unknown) == OccupancyState::Unknown,
              "The lower boundary is inside the hold range");
static_assert(nextOccupancyState(55.0f, 40.0f, 55.0f, OccupancyState::Unknown) == OccupancyState::Unknown,
              "The upper boundary is inside the hold range");
static_assert(nextOccupancyState(35.0f, 40.0f, 55.0f, OccupancyState::Unknown) == OccupancyState::Occupied,
              "A first measurement below the lower threshold establishes occupancy");
static_assert(nextOccupancyState(60.0f, 40.0f, 55.0f, OccupancyState::Unknown) == OccupancyState::Free,
              "A first measurement above the upper threshold establishes availability");
static_assert(nextOccupancyState(48.0f, 40.0f, 55.0f, OccupancyState::Occupied) == OccupancyState::Occupied,
              "Keep the measured occupied state between thresholds");
static_assert(nextOccupancyState(48.0f, 40.0f, 55.0f, OccupancyState::Free) == OccupancyState::Free,
              "Keep the measured free state between thresholds");
#endif
