import { apiFetch } from "./base";

export const getInitial = (count) =>
  apiFetch(`/words/initial?count=${count}`);
export const updateWord = (id, { polish, english, ukrainian }) =>
  apiFetch(`/words/${id}`, { method: "PUT", body: { polish, english, ukrainian } });
export const checkWord = (text) =>
  apiFetch("/words/check", { method: "POST", body: { text } });
export const checkWordsBulk = (text) =>
  apiFetch("/words/check/bulk", { method: "POST", body: { text } });
