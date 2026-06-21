import { apiFetch } from "./base";

export const getSession = () => apiFetch("/session");
export const getAllWords = () => apiFetch("/session/words/all");
export const setLanguage = (language_set) =>
  apiFetch("/session/language", { method: "PUT", body: { language_set } });
export const addWord = (word_id) =>
  apiFetch("/session/words", { method: "POST", body: { word_id } });
export const addWordsBulk = (word_ids) =>
  apiFetch("/session/words/bulk", { method: "POST", body: { word_ids } });
export const toggleWord = (word_id, enabled) =>
  apiFetch("/session/words/toggle", { method: "PUT", body: { word_id, enabled } });
export const deleteWord = (word_id) =>
  apiFetch(`/session/words/${word_id}`, { method: "DELETE" });
