import { apiFetch, API_BASE_URL } from "./base";

export const validate = (payload) =>
  apiFetch("/practice/validate", { method: "POST", body: payload });
export const skip = (payload) =>
  apiFetch("/practice/skip", { method: "POST", body: payload });

export const chooseQuestion = ({ language_set, direction, exclude_word_id }) => {
  const params = new URLSearchParams({ language_set, direction });
  if (exclude_word_id !== undefined && exclude_word_id !== null) {
    params.set("exclude_word_id", exclude_word_id);
  }
  return apiFetch(`/practice/choose-translation/question?${params}`);
};

export const chooseValidate = (payload) =>
  apiFetch("/practice/choose-translation/validate", { method: "POST", body: payload });

// Pronunciation submit reads JSON (non-raw); body is a FormData.
export const submitPronunciation = (formData) =>
  apiFetch("/practice/pronunciation", { method: "POST", body: formData });

// Pure URL builder for the TTS blob endpoint (caller fetches the blob directly).
export const ttsUrl = (text) =>
  `${API_BASE_URL}/practice/tts?text=${encodeURIComponent(text)}`;
