// Single source of truth for react-query refetchInterval values across the
// dashboard. Mismatched intervals were causing the Jobs page count, the
// Statistics card, and the header session badge to disagree visibly while
// a scrape was in flight — see consensus.md in
// .paircode/focus-03-ui-inconsistency-during-scrape/.
//
// Bump LIVE_POLL_MS only if every consumer is happy with the cadence.

export const LIVE_POLL_MS = 2000
