import { apiFetch } from "./base";

export const getStats = () => apiFetch("/stats");

export const getHistory = ({ limit, language_set }) => {
  const params = new URLSearchParams();
  if (limit !== undefined && limit !== null) params.set("limit", limit);
  if (language_set !== undefined && language_set !== null) params.set("language_set", language_set);
  return apiFetch(`/stats/history?${params}`);
};

export const explain = (payload) =>
  apiFetch("/stats/explain", { method: "POST", body: payload });
