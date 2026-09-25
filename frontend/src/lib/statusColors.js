// Single source of truth for status -> color, shared by map markers and
// list/panel badges so the console reads consistently everywhere.
export const RIDER_STATUS_COLOR = {
  active: "var(--color-status-active)",
  broken_down: "var(--color-status-broken)",
  offline: "var(--color-status-offline)",
};

export const RIDER_STATUS_LABEL = {
  active: "Active",
  broken_down: "Broken down",
  offline: "Offline",
};

export const ORDER_STATUS_COLOR = {
  UNASSIGNED: "var(--color-status-unassigned)",
  ASSIGNED: "var(--color-status-assigned)",
  IN_TRANSIT: "var(--color-status-transit)",
  DELIVERED: "var(--color-status-delivered)",
  FAILED: "var(--color-status-failed)",
  UNPLACED: "var(--color-status-unplaced)",
};

export const ORDER_STATUS_LABEL = {
  UNASSIGNED: "Unassigned",
  ASSIGNED: "Assigned",
  IN_TRANSIT: "In transit",
  DELIVERED: "Delivered",
  FAILED: "Failed",
  UNPLACED: "Unplaced",
};
