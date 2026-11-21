#pragma once
#include <stdint.h>

constexpr bool shouldRefreshSas(uint64_t now, uint64_t expiry, uint32_t refreshBefore) {
  return expiry == 0 || now >= expiry || expiry - now <= refreshBefore;
}

#ifdef SAS_REFRESH_TEST
static_assert(shouldRefreshSas(1000, 0, 300), "Missing token");
static_assert(!shouldRefreshSas(1000, 1301, 300), "Keep unexpired token outside renewal window");
static_assert(shouldRefreshSas(1000, 1300, 300), "Renew at window boundary");
static_assert(shouldRefreshSas(1000, 1000, 300), "Renew at expiry");
static_assert(shouldRefreshSas(1001, 1000, 300), "Renew expired token without unsigned underflow");
#endif
