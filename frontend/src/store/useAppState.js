import { createContext, useContext, useReducer, createElement } from "react";

const AppStateContext = createContext(null);

const initialState = {
  riders: {},
  orders: {},
  proposals: {},
  auditLog: [],
  loading: true,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_RIDERS": {
      const riders = {};
      action.payload.forEach((r) => (riders[r.id] = r));
      return { ...state, riders };
    }
    case "SET_ORDERS": {
      const orders = {};
      action.payload.forEach((o) => (orders[o.id] = o));
      return { ...state, orders };
    }
    case "SET_PROPOSALS": {
      const proposals = {};
      action.payload.forEach((p) => (proposals[p.id] = p));
      return { ...state, proposals };
    }
    case "SET_AUDIT_LOG":
      return { ...state, auditLog: action.payload };
    case "UPSERT_ORDER":
      return { ...state, orders: { ...state.orders, [action.payload.id]: action.payload } };
    case "UPSERT_PROPOSAL":
      return { ...state, proposals: { ...state.proposals, [action.payload.id]: action.payload } };
    case "PATCH_RIDERS": {
      const riders = { ...state.riders };
      action.payload.forEach((r) => {
        riders[r.id] = { ...riders[r.id], ...r };
      });
      return { ...state, riders };
    }
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

// Plain .js file (no JSX) so it runs under Vite's default esbuild loader for .js.
export function AppStateProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return createElement(AppStateContext.Provider, { value: { state, dispatch } }, children);
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}