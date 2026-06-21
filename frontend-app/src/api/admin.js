import { apiFetch } from "./base";

export const getDevices = () => apiFetch("/admin/devices");
export const deleteDevice = (id) =>
  apiFetch(`/admin/devices/${id}`, { method: "DELETE" });
export const clearDevices = () =>
  apiFetch("/admin/devices", { method: "DELETE" });

export const getSettings = () => apiFetch("/admin/settings");
export const getSetting = (key) => apiFetch(`/admin/settings/${key}`);
export const updateSetting = (key, value) =>
  apiFetch(`/admin/settings/${key}`, { method: "PUT", body: { value } });

export const getSentences = () => apiFetch("/admin/sentences");
export const saveSentence = (id, { sentence, correct_answer }) =>
  apiFetch(`/admin/sentences/${id}`, { method: "PUT", body: { sentence, correct_answer } });
export const fixSentence = (id) =>
  apiFetch(`/admin/sentences/${id}/fix`, { method: "POST" });
export const deleteSentence = (id) =>
  apiFetch(`/admin/sentences/${id}`, { method: "DELETE" });
