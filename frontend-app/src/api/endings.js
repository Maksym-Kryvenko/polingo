import { apiFetch } from "./base";

export const getConfig = () => apiFetch("/endings/config");

export const getQuestion = ({ part_of_speech, cases, tenses, exclude_word_id }) => {
  const params = new URLSearchParams({ part_of_speech });
  if (tenses !== undefined && tenses !== null) params.set("tenses", tenses);
  if (cases !== undefined && cases !== null) params.set("cases", cases);
  if (exclude_word_id !== undefined && exclude_word_id !== null) {
    params.set("exclude_word_id", exclude_word_id);
  }
  return apiFetch(`/endings/question?${params}`);
};

export const validate = ({ word_id, answer, correct_answer }) =>
  apiFetch("/endings/validate", { method: "POST", body: { word_id, answer, correct_answer } });

export const getStats = () => apiFetch("/endings/stats");
