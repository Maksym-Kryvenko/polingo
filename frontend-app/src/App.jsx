import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import * as api from "./api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:8000/api`;

function shuffleArray(array) {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function renderSpellingDiff(userAnswer, correctAnswer) {
  const result = [];
  const maxLen = Math.max(userAnswer.length, correctAnswer.length);
  for (let i = 0; i < maxLen; i++) {
    const userChar = userAnswer[i] || "";
    const correctChar = correctAnswer[i] || "";
    if (userChar.toLowerCase() !== correctChar.toLowerCase()) {
      if (userChar) result.push(<span key={i} className="char-incorrect">{userChar}</span>);
      if (!userAnswer[i] && correctChar) result.push(<span key={`m-${i}`} className="char-missing">{correctChar}</span>);
    } else {
      result.push(<span key={i} className="char-correct">{userChar}</span>);
    }
  }
  return result;
}

const LANGUAGE_LABELS = { english: "English", ukrainian: "Ukrainian" };
const FIELD_LABELS = { polish: "Polish entry", english: "English entry", ukrainian: "Ukrainian entry", resolved: "LLM match" };
const buildUrl = (path) => `${API_BASE_URL}/${path}`;
const STATUS_HIDE_DELAY = 5000;

function getInitialPage() {
  const hash = window.location.hash.replace("#", "");
  const valid = ["home", "add", "practice", "pronunciation", "endings", "manage", "admin", "stats-detail"];
  return valid.includes(hash) ? hash : "home";
}

function App() {
  const [activePage, setActivePage] = useState(getInitialPage);

  // Keep URL hash in sync with activePage
  useEffect(() => {
    const newHash = activePage === "home" ? "" : activePage;
    if (window.location.hash.replace("#", "") !== newHash) {
      window.location.hash = newHash;
    }
  }, [activePage]);

  // Handle browser back/forward
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      const valid = ["home", "add", "practice", "pronunciation", "endings", "manage", "admin", "stats-detail"];
      setActivePage(valid.includes(hash) ? hash : "home");
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const [languageSet, setLanguageSet] = useState("english");
  const [manualEntry, setManualEntry] = useState("");
  const [manualStatus, setManualStatus] = useState(null);
  const [addingWords, setAddingWords] = useState(false);
  const [wordPool, setWordPool] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Unified practice state
  const [practiceMode, setPracticeMode] = useState("translation"); // translation | writing | choose
  const [practiceDirection, setPracticeDirection] = useState("from_polish");
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [practiceStatus, setPracticeStatus] = useState(null);
  const [shuffledWords, setShuffledWords] = useState([]);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [chooseQuestion, setChooseQuestion] = useState(null);
  const practiceStatusTimeoutRef = useRef(null);

  // Pronunciation state
  const [isRecording, setIsRecording] = useState(false);
  const [pronunciationStatus, setPronunciationStatus] = useState(null);
  const [pronunciationIndex, setPronunciationIndex] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const pronunciationStatusTimeoutRef = useRef(null);

  // Endings state
  const [endingsConfig, setEndingsConfig] = useState(null);
  const [endingsPoS, setEndingsPoS] = useState("rzeczownik");
  const [endingsCases, setEndingsCases] = useState(["biernik"]);
  const [endingsTenses, setEndingsTenses] = useState(["teraźniejszy"]);
  const [endingsMode, setEndingsMode] = useState("choose"); // choose | write
  const [endingsQuestion, setEndingsQuestion] = useState(null);
  const [endingsStatus, setEndingsStatus] = useState(null);
  const [endingsStats, setEndingsStats] = useState(null);
  const [endingsWriteAnswer, setEndingsWriteAnswer] = useState("");
  const [showGrammar, setShowGrammar] = useState(false);
  const endingsStatusTimeoutRef = useRef(null);

  // Manage state
  const [allWords, setAllWords] = useState([]);
  const [editingWordId, setEditingWordId] = useState(null);
  const [editingValues, setEditingValues] = useState({ polish: "", english: "", ukrainian: "" });
  const [editSaving, setEditSaving] = useState(false);
  const [manageFilterPoS, setManageFilterPoS] = useState(new Set());
  const toggleManageFilter = (tag) => setManageFilterPoS((prev) => { if (tag === "all") return new Set(); const next = new Set(prev); next.has(tag) ? next.delete(tag) : next.add(tag); return next.size === 0 ? new Set() : next; });

  // Admin state
  const [connectedDevices, setConnectedDevices] = useState([]);
  const [deviceStats, setDeviceStats] = useState({ total: 0, active: 0 });
  const adminPollIntervalRef = useRef(null);
  const [generateOnTheFly, setGenerateOnTheFly] = useState(false);
  const [ttsSource, setTtsSource] = useState("browser");
  const [sentences, setSentences] = useState([]);
  const [editingSentenceId, setEditingSentenceId] = useState(null);
  const [editingSentenceValues, setEditingSentenceValues] = useState({ sentence: "", correct_answer: "" });
  const [sentenceFixingId, setSentenceFixingId] = useState(null);
  const [sentenceFilterPoS, setSentenceFilterPoS] = useState(new Set());
  const toggleSentencePoS = (tag) => setSentenceFilterPoS((prev) => { if (tag === "all") return new Set(); const next = new Set(prev); next.has(tag) ? next.delete(tag) : next.add(tag); return next.size === 0 ? new Set() : next; });
  const [sentenceFilterMeta, setSentenceFilterMeta] = useState(new Set());
  const toggleSentenceMeta = (tag) => setSentenceFilterMeta((prev) => { if (tag === "all") return new Set(); const next = new Set(prev); next.has(tag) ? next.delete(tag) : next.add(tag); return next.size === 0 ? new Set() : next; });

  // Stats detail / history state
  const [historyRecords, setHistoryRecords] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedExplain, setExpandedExplain] = useState(null); // record id
  const [explainText, setExplainText] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);

  // Collapsible settings state
  const [showPracticeSettings, setShowPracticeSettings] = useState(false);
  const [showEndingsSettings, setShowEndingsSettings] = useState(false);

  // ── Fetch helpers ─────────────────────────────────────────
  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const data = await api.stats.getStats();
      if (data) setStats(data);
    } catch (e) { console.error(e); }
    finally { setLoadingStats(false); }
  };

  const fetchSession = async () => {
    try {
      const data = await api.session.getSession();
      if (data) {
        setLanguageSet(data.language_set);
        setWordPool(data.words ?? []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchAllWords = async () => {
    try {
      const data = await api.session.getAllWords();
      if (data) {
        setAllWords(data.words ?? []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchEndingsConfig = async () => {
    try {
      const data = await api.endings.getConfig();
      if (data) setEndingsConfig(data);
    } catch (e) { console.error(e); }
  };

  const fetchEndingsQuestion = async () => {
    try {
      const data = await api.endings.getQuestion({
        part_of_speech: endingsPoS,
        tenses: endingsPoS === "czasownik" ? endingsTenses.join(",") : undefined,
        cases: endingsPoS === "czasownik" ? undefined : endingsCases.join(","),
        exclude_word_id: endingsQuestion?.word_id || undefined,
      });
      setEndingsQuestion(data ?? null);
    } catch (e) { console.error(e); setEndingsQuestion(null); }
  };

  const fetchEndingsStats = async () => {
    try {
      const data = await api.endings.getStats();
      if (data) setEndingsStats(data);
    } catch (e) { console.error(e); }
  };

  const fetchChooseQuestion = async () => {
    try {
      const data = await api.practice.chooseQuestion({
        language_set: languageSet,
        direction: practiceDirection,
        exclude_word_id: chooseQuestion?.word_id || undefined,
      });
      setChooseQuestion(data ?? null);
    } catch (e) { console.error(e); setChooseQuestion(null); }
  };

  const fetchConnectedDevices = async () => {
    try {
      const r = await fetch(buildUrl("admin/devices"));
      if (r.ok) {
        const data = await r.json();
        setConnectedDevices(data.devices);
        setDeviceStats({ total: data.total_count, active: data.active_count });
      }
    } catch (e) { console.error(e); }
  };

  const fetchAdminSettings = async () => {
    try {
      const r = await fetch(buildUrl("admin/settings"));
      if (r.ok) {
        const data = await r.json();
        const otf = data.find((s) => s.key === "generate_on_the_fly");
        setGenerateOnTheFly(otf?.value === "true");
        const tts = data.find((s) => s.key === "tts_source");
        setTtsSource(tts?.value ?? "browser");
      }
    } catch (e) { console.error(e); }
  };

  const fetchTtsSetting = async () => {
    try {
      const r = await fetch(buildUrl("admin/settings/tts_source"));
      if (r.ok) {
        const data = await r.json();
        setTtsSource(data.value ?? "browser");
      }
    } catch (e) { /* setting may not exist yet, keep default */ }
  };

  const toggleOnTheFly = async () => {
    const newVal = !generateOnTheFly;
    try {
      await fetch(buildUrl("admin/settings/generate_on_the_fly"), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: newVal ? "true" : "false" }),
      });
      setGenerateOnTheFly(newVal);
    } catch (e) { console.error(e); }
  };

  const toggleTtsSource = async () => {
    const newVal = ttsSource === "browser" ? "server" : "browser";
    try {
      await fetch(buildUrl("admin/settings/tts_source"), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: newVal }),
      });
      setTtsSource(newVal);
    } catch (e) { console.error(e); }
  };

  const ttsCache = useRef({});

  const playPronunciation = async (text) => {
    if (!text) return;
    if (ttsSource === "server") {
      try {
        let url = ttsCache.current[text];
        if (!url) {
          const r = await fetch(api.practice.ttsUrl(text)); // raw: blob
          if (!r.ok) return;
          const blob = await r.blob();
          url = URL.createObjectURL(blob);
          ttsCache.current[text] = url;
        }
        const audio = new Audio(url);
        audio.play();
      } catch (e) { console.error(e); }
    } else {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "pl-PL";
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  };

  const fetchSentences = async () => {
    try {
      const r = await fetch(buildUrl("admin/sentences"));
      if (r.ok) setSentences(await r.json());
    } catch (e) { console.error(e); }
  };

  const handleSaveSentence = async (id) => {
    try {
      const r = await fetch(buildUrl(`admin/sentences/${id}`), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editingSentenceValues),
      });
      if (r.ok) {
        const updated = await r.json();
        setSentences((prev) => prev.map((s) => s.id === id ? updated : s));
        setEditingSentenceId(null);
      }
    } catch (e) { console.error(e); }
  };

  const handleFixSentence = async (id) => {
    setSentenceFixingId(id);
    try {
      const r = await fetch(buildUrl(`admin/sentences/${id}/fix`), { method: "POST" });
      if (r.ok) {
        const updated = await r.json();
        setSentences((prev) => prev.map((s) => s.id === id ? updated : s));
      }
    } catch (e) { console.error(e); }
    finally { setSentenceFixingId(null); }
  };

  const handleDeleteSentence = async (id) => {
    try {
      const r = await fetch(buildUrl(`admin/sentences/${id}`), { method: "DELETE" });
      if (r.ok) setSentences((prev) => prev.filter((s) => s.id !== id));
    } catch (e) { console.error(e); }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await api.stats.getHistory({ limit: 100, language_set: languageSet });
      if (data) {
        setHistoryRecords(data.records ?? []);
        setHistoryTotal(data.total ?? 0);
      }
    } catch (e) { console.error(e); }
    finally { setHistoryLoading(false); }
  };

  const fetchExplain = async (record) => {
    setExpandedExplain(record.id);
    setExplainText("");
    setExplainLoading(true);
    try {
      const data = await api.stats.explain({
        word_polish: record.word_polish,
        word_translation: record.word_translation,
        section: record.section,
        user_answer: record.user_answer,
        correct_answer: record.correct_answer,
        was_correct: record.was_correct,
      });
      if (data) {
        setExplainText(data.explanation);
      } else {
        setExplainText("Could not get explanation.");
      }
    } catch (e) { console.error(e); setExplainText("Error fetching explanation."); }
    finally { setExplainLoading(false); }
  };

  // ── Effects ───────────────────────────────────────────────
  useEffect(() => { fetchStats(); fetchSession(); fetchEndingsConfig(); fetchTtsSetting(); }, []);

  useEffect(() => {
    if (activePage === "manage") fetchAllWords();
    if (activePage === "stats-detail") fetchHistory();
    if (activePage === "admin") {
      fetchConnectedDevices();
      fetchAdminSettings();
      fetchSentences();
      adminPollIntervalRef.current = setInterval(fetchConnectedDevices, 5000);
    }
    return () => { if (adminPollIntervalRef.current) { clearInterval(adminPollIntervalRef.current); adminPollIntervalRef.current = null; } };
  }, [activePage]);

  useEffect(() => {
    setAnswer("");
    setPracticeStatus(null);
    setPracticeIndex(0);
    setLastAnswer(null);
    setChooseQuestion(null);
    setPronunciationStatus(null);
    setPronunciationIndex(0);
    setEndingsStatus(null);
    setEndingsQuestion(null);
    setEndingsWriteAnswer("");
    setShowGrammar(false);

    if (activePage === "practice") {
      setShuffledWords(shuffleArray(wordPool));
      if (practiceMode === "choose") fetchChooseQuestion();
    }
    if (activePage === "pronunciation") setShuffledWords(shuffleArray(wordPool));
    if (activePage === "endings") { fetchEndingsQuestion(); fetchEndingsStats(); }
  }, [activePage, languageSet, wordPool]);

  // Refetch choose question when direction or mode changes
  useEffect(() => {
    if (activePage === "practice" && practiceMode === "choose") fetchChooseQuestion();
  }, [practiceDirection, practiceMode]);

  // Computed values
  const currentWriteTranslateWord = shuffledWords.length ? shuffledWords[practiceIndex % shuffledWords.length] : null;
  const currentPronunciationWord = activePage === "pronunciation" && shuffledWords.length ? shuffledWords[pronunciationIndex % shuffledWords.length] : null;
  const targetLabel = LANGUAGE_LABELS[languageSet];
  const dictionarySize = stats?.available_words ?? 0;
  const readinessBar = wordPool.length ? `${Math.min((wordPool.length / 30) * 100, 100)}%` : "0%";

  const statsSummary = useMemo(() => {
    if (!stats) return { today: "--", trend: "--", overall: "--" };
    const trend = stats.trend >= 0 ? `+${stats.trend}` : `${stats.trend}`;
    return { today: `${stats.today_percentage}%`, trend: `${trend}%`, overall: `${stats.overall_percentage}%` };
  }, [stats]);

  // ── Practice handlers ─────────────────────────────────────
  const handleLanguageChange = async (value) => {
    setLanguageSet(value);
    try { await api.session.setLanguage(value); } catch (e) { console.error(e); }
  };

  const handleLoadInitial = async () => {
    try {
      const r = await fetch(buildUrl("words/initial?count=10"));
      if (!r.ok) throw new Error();
      const payload = await r.json();
      const saved = await fetch(buildUrl("session/words/bulk"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_ids: payload.map((w) => w.id) }) });
      if (!saved.ok) throw new Error();
      const ss = await saved.json();
      setWordPool(ss.words ?? []);
      setManualStatus({ type: "success", message: "Loaded and saved the first 10 words." });
    } catch (e) { console.error(e); setManualStatus({ type: "error", message: "Could not load starter set." }); }
  };

  const handleManualSubmit = async () => {
    const trimmed = manualEntry.trim();
    if (!trimmed) { setManualStatus({ type: "error", message: "Type a word or phrase." }); return; }
    setAddingWords(true);
    try {
      if (trimmed.includes(",")) {
        const r = await fetch(buildUrl("words/check/bulk"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: trimmed }) });
        if (!r.ok) throw new Error();
        const p = await r.json();
        await fetchSession();
        const msgs = [];
        if (p.added_count > 0) msgs.push(`Added ${p.added_count} word(s)`);
        if (p.duplicate_count > 0) msgs.push(`${p.duplicate_count} already in session`);
        if (p.failed_count > 0) msgs.push(`${p.failed_count} could not be found`);
        setManualStatus({ type: p.added_count > 0 ? "success" : (p.duplicate_count > 0 ? "info" : "error"), message: msgs.join(". ") + "." });
      } else {
        const r = await fetch(buildUrl("words/check"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: trimmed }) });
        if (!r.ok) throw new Error();
        const p = await r.json();
        if (!p.found || !p.word) { setManualStatus({ type: "error", message: "Word not found. Check spelling or try a different form." }); return; }
        const saved = await fetch(buildUrl("session/words"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: p.word.id }) });
        if (!saved.ok) throw new Error();
        const ss = await saved.json();
        setWordPool(ss.words ?? []);
        const src = FIELD_LABELS[p.matched_field] ?? "entry";
        const extra = p.created ? "Added via GPT." : "";
        setManualStatus({ type: "success", message: `Saved ${p.word.polish} (${src}). ${extra}`.trim() });
      }
    } catch (e) { console.error(e); setManualStatus({ type: "error", message: "Something went wrong. Try again." }); }
    finally { setManualEntry(""); setAddingWords(false); }
  };

  const handlePracticeSubmit = async (event) => {
    event?.preventDefault?.();
    if (!currentWriteTranslateWord) return;
    if (practiceStatusTimeoutRef.current) clearTimeout(practiceStatusTimeoutRef.current);
    if (!answer.trim()) { setPracticeStatus({ type: "error", message: "Try answering first." }); return; }
    const dir = practiceMode === "writing" ? "writing" : "translation";
    try {
      const p = await api.practice.validate({ word_id: currentWriteTranslateWord.id, language_set: languageSet, direction: dir, answer });
      if (!p) throw new Error();
      setPracticeStatus({ type: p.was_correct ? "success" : "error", message: p.was_correct ? "Correct!" : `The correct answer is "${p.correct_answer}".` });
      setStats(p.stats);
      setLastAnswer({ userAnswer: answer, correctAnswer: p.correct_answer, alternatives: p.alternatives || [], wasCorrect: p.was_correct, direction: dir, skipped: false });
      practiceStatusTimeoutRef.current = setTimeout(() => { setPracticeStatus(null); setLastAnswer(null); }, STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); setPracticeStatus({ type: "error", message: "Could not record. Try again." }); }
    setAnswer("");
    setPracticeIndex((i) => (i + 1) % shuffledWords.length);
  };

  const handlePracticeSkip = async () => {
    if (!currentWriteTranslateWord) return;
    if (practiceStatusTimeoutRef.current) clearTimeout(practiceStatusTimeoutRef.current);
    const dir = practiceMode === "writing" ? "writing" : "translation";
    try {
      const p = await api.practice.skip({ word_id: currentWriteTranslateWord.id, language_set: languageSet, direction: dir, answer: "" });
      if (!p) throw new Error();
      setLastAnswer({ userAnswer: "", correctAnswer: p.correct_answer, alternatives: p.alternatives || [], wasCorrect: false, direction: dir, skipped: true });
      setPracticeStatus({ type: "info", message: "Skipped. The answer was:" });
      setStats(p.stats);
      practiceStatusTimeoutRef.current = setTimeout(() => { setPracticeStatus(null); setLastAnswer(null); }, STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); }
    setAnswer("");
    setPracticeIndex((i) => (i + 1) % shuffledWords.length);
  };

  const handleChooseAnswer = async (selected) => {
    if (!chooseQuestion) return;
    if (practiceStatusTimeoutRef.current) clearTimeout(practiceStatusTimeoutRef.current);
    try {
      const p = await api.practice.chooseValidate({ word_id: chooseQuestion.word_id, language_set: languageSet, direction: practiceDirection, answer: selected });
      if (!p) throw new Error();
      setPracticeStatus({ type: p.was_correct ? "success" : "error", message: p.was_correct ? "Correct!" : `Incorrect. The answer was "${p.correct_answer}".` });
      setStats(p.stats);
      fetchChooseQuestion();
      practiceStatusTimeoutRef.current = setTimeout(() => setPracticeStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); setPracticeStatus({ type: "error", message: "Could not validate." }); }
  };

  const handleChooseSkip = async () => {
    if (!chooseQuestion) return;
    if (practiceStatusTimeoutRef.current) clearTimeout(practiceStatusTimeoutRef.current);
    try {
      await api.practice.chooseValidate({ word_id: chooseQuestion.word_id, language_set: languageSet, direction: practiceDirection, answer: "" });
      setPracticeStatus({ type: "info", message: `Skipped. The answer was "${chooseQuestion.correct_answer}".` });
      fetchChooseQuestion();
      practiceStatusTimeoutRef.current = setTimeout(() => setPracticeStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); }
  };

  // ── Pronunciation ─────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mr;
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = async () => { const blob = new Blob(audioChunksRef.current, { type: "audio/webm" }); stream.getTracks().forEach((t) => t.stop()); await submitPronunciation(blob); };
      mr.start();
      setIsRecording(true);
      setPronunciationStatus({ type: "info", message: "Recording… Click Stop when done." });
    } catch (e) { console.error(e); setPronunciationStatus({ type: "error", message: "Could not access microphone." }); }
  };

  const stopRecording = () => { if (mediaRecorderRef.current && isRecording) { mediaRecorderRef.current.stop(); setIsRecording(false); setPronunciationStatus({ type: "info", message: "Processing…" }); } };

  const submitPronunciation = async (audioBlob) => {
    if (!currentPronunciationWord) return;
    if (pronunciationStatusTimeoutRef.current) clearTimeout(pronunciationStatusTimeoutRef.current);
    const fd = new FormData();
    fd.append("audio", audioBlob, "recording.webm");
    fd.append("word_id", currentPronunciationWord.id);
    fd.append("language_set", languageSet);
    try {
      const p = await api.practice.submitPronunciation(fd);
      if (!p) throw new Error();
      const pct = Math.round(p.similarity_score * 100);
      setPronunciationStatus({ type: p.was_correct ? "success" : "error", message: p.was_correct ? `Correct! "${p.transcribed_text}" (${pct}% match)` : `You said "${p.transcribed_text}". Expected "${p.expected_word}". ${p.feedback}` });
      setStats(p.stats);
      pronunciationStatusTimeoutRef.current = setTimeout(() => setPronunciationStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); setPronunciationStatus({ type: "error", message: "Could not validate pronunciation." }); }
  };

  const handlePronunciationSkip = async () => {
    if (!currentPronunciationWord) return;
    if (pronunciationStatusTimeoutRef.current) clearTimeout(pronunciationStatusTimeoutRef.current);
    try {
      const p = await api.practice.skip({ word_id: currentPronunciationWord.id, language_set: languageSet, direction: "pronunciation", answer: "" });
      if (p) { setStats(p.stats); }
      setPronunciationStatus({ type: "info", message: `Skipped. The word was "${currentPronunciationWord.polish}".` });
      pronunciationStatusTimeoutRef.current = setTimeout(() => setPronunciationStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); }
    setPronunciationIndex((i) => (i + 1) % shuffledWords.length);
  };

  // ── Endings handlers ──────────────────────────────────────
  const handleEndingsAnswer = async (selected) => {
    if (!endingsQuestion) return;
    if (endingsStatusTimeoutRef.current) clearTimeout(endingsStatusTimeoutRef.current);
    const answerText = selected || endingsWriteAnswer.trim();
    if (!answerText) return;
    try {
      const p = await api.endings.validate({ word_id: endingsQuestion.word_id, answer: answerText, correct_answer: endingsQuestion.correct_answer });
      if (!p) throw new Error();
      setEndingsStatus({ type: p.was_correct ? "success" : "error", message: p.was_correct ? "Correct!" : `Incorrect. The answer was "${p.correct_answer}".` });
      setEndingsStats(p.stats);
      setEndingsWriteAnswer("");
      fetchEndingsQuestion();
      endingsStatusTimeoutRef.current = setTimeout(() => setEndingsStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); setEndingsStatus({ type: "error", message: "Could not validate." }); }
  };

  const handleEndingsSkip = async () => {
    if (!endingsQuestion) return;
    if (endingsStatusTimeoutRef.current) clearTimeout(endingsStatusTimeoutRef.current);
    try {
      await api.endings.validate({ word_id: endingsQuestion.word_id, answer: "", correct_answer: endingsQuestion.correct_answer });
      setEndingsStatus({ type: "info", message: `Skipped. The answer was "${endingsQuestion.correct_answer}".` });
      await fetchEndingsStats();
      setEndingsWriteAnswer("");
      fetchEndingsQuestion();
      endingsStatusTimeoutRef.current = setTimeout(() => setEndingsStatus(null), STATUS_HIDE_DELAY);
    } catch (e) { console.error(e); }
  };

  const toggleCase = (c) => setEndingsCases((prev) => prev.includes(c) ? (prev.length > 1 ? prev.filter((x) => x !== c) : prev) : [...prev, c]);
  const toggleTense = (t) => setEndingsTenses((prev) => prev.includes(t) ? (prev.length > 1 ? prev.filter((x) => x !== t) : prev) : [...prev, t]);

  // Refetch endings question when config changes
  useEffect(() => {
    if (activePage === "endings") fetchEndingsQuestion();
  }, [endingsPoS, endingsCases, endingsTenses]);

  // ── Manage handlers ───────────────────────────────────────
  const handleToggleWord = async (wordId, enabled) => {
    try {
      const r = await fetch(buildUrl("session/words/toggle"), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: wordId, enabled }) });
      if (r.ok) { const d = await r.json(); setAllWords(d.words ?? []); await fetchSession(); }
    } catch (e) { console.error(e); }
  };

  const handleDeleteWord = async (wordId) => {
    if (!window.confirm("Permanently delete this word?")) return;
    try {
      const r = await fetch(buildUrl(`session/words/${wordId}`), { method: "DELETE" });
      if (r.ok) { setAllWords((prev) => prev.filter((w) => w.id !== wordId)); await fetchSession(); }
    } catch (e) { console.error(e); }
  };

  const handleStartEditWord = (word) => { setEditingWordId(word.id); setEditingValues({ polish: word.polish, english: word.english, ukrainian: word.ukrainian }); };
  const handleCancelEdit = () => { setEditingWordId(null); setEditingValues({ polish: "", english: "", ukrainian: "" }); };
  const handleSaveEdit = async (wordId) => {
    setEditSaving(true);
    try {
      const r = await fetch(buildUrl(`words/${wordId}`), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(editingValues) });
      if (r.ok) {
        const updated = await r.json();
        setAllWords((prev) => prev.map((w) => (w.id === wordId ? { ...w, ...updated } : w)));
        setEditingWordId(null);
        setEditingValues({ polish: "", english: "", ukrainian: "" });
        await fetchSession();
      }
    } catch (e) { console.error(e); }
    finally { setEditSaving(false); }
  };

  // ── Admin handlers ────────────────────────────────────────
  const handleDeleteDevice = async (deviceId) => {
    try { await fetch(buildUrl(`admin/devices/${deviceId}`), { method: "DELETE" }); fetchConnectedDevices(); } catch (e) { console.error(e); }
  };
  const handleClearAllDevices = async () => {
    try { await fetch(buildUrl("admin/devices"), { method: "DELETE" }); fetchConnectedDevices(); } catch (e) { console.error(e); }
  };

  // ── Render ────────────────────────────────────────────────
  const writingPrompt = currentWriteTranslateWord ? currentWriteTranslateWord[languageSet] : null;
  const translationPrompt = currentWriteTranslateWord ? currentWriteTranslateWord.polish : null;

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Polingo</p>
          <h1>Polish practice that respects your tempo</h1>
          <p className="lede">
            Your session is saved automatically. Add words, practice, and come back later.
          </p>
        </div>
        <div className="stats-card clickable" onClick={() => setActivePage("stats-detail")} title="Click for detailed statistics">
          <div>
            <p className="label">Today</p>
            <h3>{statsSummary.today}</h3>
            <p className="trend">{loadingStats ? "loading…" : `Trend (${statsSummary.trend})`}</p>
          </div>
          <div className="stats-divider" aria-hidden="true" />
          <div>
            <p className="label">Overall</p>
            <h3>{statsSummary.overall}</h3>
          </div>
        </div>
      </header>

      <main className="layout">
        {/* ── HOME ─────────────────────────────────────── */}
        {activePage === "home" && (
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="subtitle">Session control</p>
                <select value={languageSet} onChange={(e) => handleLanguageChange(e.target.value)} className="language-select">
                  <option value="english">Polish + English</option>
                  <option value="ukrainian">Polish + Ukrainian</option>
                </select>
              </div>
              <div className="readiness">
                <p className="subtitle">Session readiness</p>
                <span>{wordPool.length} words</span>
                <p className="subtitle">Available in database</p>
                <span>{dictionarySize} words</span>
              </div>
            </div>
            <div className="progress-track"><span style={{ width: readinessBar }} /></div>
            <div className="nav-grid">
              <button className="nav-card" onClick={() => setActivePage("add")} type="button">
                <p className="subtitle">Add words</p>
                <h3>Build your session list</h3>
                <p>Validate new entries or load the starter set.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("practice")} type="button">
                <p className="subtitle">Practice</p>
                <h3>Translation &amp; Writing</h3>
                <p>Write or choose translations in different modes.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("pronunciation")} type="button">
                <p className="subtitle">Pronunciation</p>
                <h3>Speak Polish words</h3>
                <p>Practice saying words and get AI feedback.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("endings")} type="button">
                <p className="subtitle">Endings</p>
                <h3>Practice declensions &amp; conjugations</h3>
                <p>Rzeczownik, przymiotnik, czasownik forms with grammar reference.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("manage")} type="button">
                <p className="subtitle">Manage</p>
                <h3>Review your word list</h3>
                <p>View all words, toggle on/off, edit translations.</p>
              </button>
            </div>
          </section>
        )}

        {/* ── ADD WORDS ────────────────────────────────── */}
        {activePage === "add" && (
          <section className="panel">
            <div className="panel-header">
              <div><p className="subtitle">Add words</p><h2>Curate your session list</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>
            <div className="instruction-card">
              <p className="step">1</p>
              <div>
                <p className="instruction-title">Validate new words</p>
                <p className="instruction-body">
                  Enter a single word or multiple words separated by commas. The system detects part of speech automatically. Duplicates are skipped.
                </p>
              </div>
            </div>
            <div className="manual-entry">
              <input value={manualEntry} onChange={(e) => setManualEntry(e.target.value)} type="text" placeholder="Type words (e.g., hello, goodbye, robić, duży)" />
              <button onClick={handleManualSubmit} disabled={addingWords}>{addingWords ? <span className="spinner" /> : "Validate & add"}</button>
            </div>
            {manualStatus && <p className={`status ${manualStatus.type}`}>{manualStatus.message}</p>}
            <div className="instruction-card">
              <p className="step">2</p>
              <div>
                <p className="instruction-title">Or load the starter list</p>
                <p className="instruction-body">These first 10 words are guaranteed in the database.</p>
              </div>
            </div>
            <button className="secondary" onClick={handleLoadInitial}>Load starter set</button>
            {wordPool.length > 0 && (
              <div className="word-preview">
                <p className="subtitle">Words to practice (ordered by difficulty)</p>
                <ul>
                  {wordPool.slice(0, 6).map((w) => (
                    <li key={w.id}>
                      <span>{w.polish}</span>
                      <span className="pos-badge">{w.part_of_speech || "inne"}</span>
                      <span>{w[languageSet]}</span>
                      <span className="error-rate">{w.total_attempts > 0 ? `${w.error_rate}% errors (${w.total_attempts} tries)` : "New"}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* ── PRACTICE (combined Translation, Writing, Choose) ── */}
        {activePage === "practice" && (
          <section className="panel practice-panel">
            <div className="panel-header">
              <div><p className="subtitle">Practice</p><h2>Translation &amp; Writing</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>

            {!shuffledWords.length && <p className="status info">Add words to your session first, then return here to practice.</p>}

            {/* Collapsible mode settings */}
            <button className="settings-toggle" onClick={() => setShowPracticeSettings(!showPracticeSettings)} type="button">
              {showPracticeSettings ? "Hide settings ▲" : "Mode settings ▼"}
            </button>
            {showPracticeSettings && (
              <>
                {/* Mode tabs */}
                <div className="mode-tabs">
                  <button className={`mode-tab ${practiceMode === "translation" ? "active" : ""}`} onClick={() => setPracticeMode("translation")} type="button">Translation</button>
                  <button className={`mode-tab ${practiceMode === "writing" ? "active" : ""}`} onClick={() => setPracticeMode("writing")} type="button">Writing</button>
                  <button className={`mode-tab ${practiceMode === "choose" ? "active" : ""}`} onClick={() => setPracticeMode("choose")} type="button">Choose</button>
                </div>

                {/* Direction selector for choose mode */}
                {practiceMode === "choose" && (
                  <div className="direction-tabs">
                    <button className={`direction-tab ${practiceDirection === "from_polish" ? "active" : ""}`} onClick={() => setPracticeDirection("from_polish")} type="button">
                      Polish → {languageSet === "english" ? "English" : "Ukrainian"}
                    </button>
                    <button className={`direction-tab ${practiceDirection === "to_polish" ? "active" : ""}`} onClick={() => setPracticeDirection("to_polish")} type="button">
                      {languageSet === "english" ? "English" : "Ukrainian"} → Polish
                    </button>
                  </div>
                )}
              </>
            )}

            <div className="practice-status">
              <p className={`status ${practiceStatus?.type ?? "info"}`}>
                {practiceStatus?.message ?? (practiceMode === "choose" ? "Select the correct translation." : "Practice results appear here.")}
              </p>
              {lastAnswer && !lastAnswer.wasCorrect && (
                <div className="answer-details">
                  {lastAnswer.direction === "writing" && lastAnswer.userAnswer && !lastAnswer.skipped && (
                    <p className="spelling-diff">Your answer: {renderSpellingDiff(lastAnswer.userAnswer, lastAnswer.correctAnswer)}</p>
                  )}
                  <p className="correct-answer">Correct: <strong>{lastAnswer.correctAnswer}</strong></p>
                  {lastAnswer.alternatives.length > 0 && <p className="alternatives">Also accepted: {lastAnswer.alternatives.join(", ")}</p>}
                </div>
              )}
              {lastAnswer && lastAnswer.wasCorrect && lastAnswer.alternatives.length > 0 && (
                <div className="answer-details"><p className="alternatives">Other accepted: {lastAnswer.alternatives.join(", ")}</p></div>
              )}
            </div>

            {/* Translation / Writing modes */}
            {(practiceMode === "translation" || practiceMode === "writing") && (
              <form onSubmit={handlePracticeSubmit} className="practice-card">
                <div className="practice-mirror">
                  <p className="subtitle">Target language: {practiceMode === "writing" ? "Polish" : targetLabel}</p>
                  <p className="prompt">
                    {practiceMode === "writing" ? (writingPrompt ?? "Add words to start.") : (translationPrompt ?? "Add words to start.")}
                    {practiceMode === "translation" && translationPrompt && (
                      <button type="button" className="listen-btn" onClick={() => playPronunciation(translationPrompt)} title="Listen to pronunciation"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg></button>
                    )}
                  </p>
                </div>
                <input value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder={practiceMode === "writing" ? "Type the Polish word…" : `Type the ${targetLabel} translation…`} disabled={!currentWriteTranslateWord} />
                <div className="practice-buttons">
                  <button type="submit" disabled={!currentWriteTranslateWord}>Submit answer</button>
                  <button type="button" className="skip-btn" onClick={handlePracticeSkip} disabled={!currentWriteTranslateWord}>Skip</button>
                </div>
              </form>
            )}

            {/* Choose mode */}
            {practiceMode === "choose" && (
              <>
                {wordPool.length < 4 && <p className="status info">Add at least 4 words to your session.</p>}
                {chooseQuestion && (
                  <div className="practice-card choose-translation-card">
                    <div className="practice-mirror">
                      <p className="subtitle">Translate {practiceDirection === "from_polish" ? "from Polish" : "to Polish"}:</p>
                      <p className="prompt choose-translation-prompt">
                        {chooseQuestion.prompt}
                        {practiceDirection === "from_polish" && (
                          <button type="button" className="listen-btn" onClick={() => playPronunciation(chooseQuestion.prompt)} title="Listen to pronunciation"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg></button>
                        )}
                      </p>
                    </div>
                    <div className="choose-translation-options">
                      {chooseQuestion.options.map((opt, i) => (
                        <button key={i} className="choose-translation-option" onClick={() => handleChooseAnswer(opt)}>{opt}</button>
                      ))}
                    </div>
                    <button className="skip-btn choose-translation-skip" onClick={handleChooseSkip}>Skip</button>
                  </div>
                )}
                {!chooseQuestion && wordPool.length >= 4 && <div className="practice-card"><p>Loading question…</p></div>}
              </>
            )}
          </section>
        )}

        {/* ── PRONUNCIATION ────────────────────────────── */}
        {activePage === "pronunciation" && (
          <section className="panel practice-panel">
            <div className="panel-header">
              <div><p className="subtitle">Practice</p><h2>Pronunciation mode</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>
            {!shuffledWords.length && <p className="status info">Add words to your session first.</p>}
            <div className="practice-status">
              <p className={`status ${pronunciationStatus?.type ?? "info"}`}>{pronunciationStatus?.message ?? "Click Record and say the Polish word shown below."}</p>
            </div>
            <div className="practice-card pronunciation-card">
              <div className="practice-mirror">
                <p className="subtitle">Say this word in Polish:</p>
                <p className="prompt pronunciation-prompt">{currentPronunciationWord?.polish ?? "Add words to start."}</p>
                {currentPronunciationWord && <p className="translation-hint">({currentPronunciationWord[languageSet]})</p>}
              </div>
              <div className="pronunciation-controls">
                {!isRecording ? (
                  <button onClick={startRecording} disabled={!currentPronunciationWord} className="record-btn">🎤 Record</button>
                ) : (
                  <button onClick={stopRecording} className="record-btn recording">⏹ Stop Recording</button>
                )}
                <button onClick={handlePronunciationSkip} disabled={!currentPronunciationWord || isRecording} className="skip-btn">Skip</button>
                <button onClick={() => setPronunciationIndex((i) => (i + 1) % shuffledWords.length)} disabled={!currentPronunciationWord || isRecording} className="secondary">Next word →</button>
              </div>
            </div>
          </section>
        )}

        {/* ── ENDINGS ──────────────────────────────────── */}
        {activePage === "endings" && (
          <section className="panel practice-panel">
            <div className="panel-header">
              <div><p className="subtitle">Practice</p><h2>Endings</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>

            {/* Collapsible config panel */}
            <button className="settings-toggle" onClick={() => setShowEndingsSettings(!showEndingsSettings)} type="button">
              {showEndingsSettings ? "Hide settings ▲" : "Mode settings ▼"}
            </button>
            {showEndingsSettings && (
              <div className="endings-config">
                <div className="config-row">
                  <span className="config-label">Part of speech:</span>
                  <div className="mode-tabs compact">
                    {(endingsConfig?.parts_of_speech ?? ["rzeczownik", "przymiotnik", "czasownik"]).map((p) => (
                      <button key={p} className={`mode-tab ${endingsPoS === p ? "active" : ""}`} onClick={() => setEndingsPoS(p)} type="button">{p}</button>
                    ))}
                  </div>
                </div>

                {endingsPoS !== "czasownik" && (
                  <div className="config-row">
                    <span className="config-label">Cases:</span>
                    <div className="chip-group">
                      {(endingsConfig?.cases ?? []).map((c) => (
                        <button key={c} className={`chip ${endingsCases.includes(c) ? "active" : ""}`} onClick={() => toggleCase(c)} type="button">{c}</button>
                      ))}
                    </div>
                  </div>
                )}

                {endingsPoS === "czasownik" && (
                  <div className="config-row">
                    <span className="config-label">Tenses:</span>
                    <div className="chip-group">
                      {(endingsConfig?.tenses ?? []).map((t) => (
                        <button key={t} className={`chip ${endingsTenses.includes(t) ? "active" : ""}`} onClick={() => toggleTense(t)} type="button">{t}</button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="config-row">
                  <span className="config-label">Mode:</span>
                  <div className="mode-tabs compact">
                    <button className={`mode-tab ${endingsMode === "choose" ? "active" : ""}`} onClick={() => setEndingsMode("choose")} type="button">Choose 1 of 4</button>
                    <button className={`mode-tab ${endingsMode === "write" ? "active" : ""}`} onClick={() => setEndingsMode("write")} type="button">Write answer</button>
                  </div>
                </div>
              </div>
            )}

            <div className="practice-status">
              <p className={`status ${endingsStatus?.type ?? "info"}`}>
                {endingsStatus?.message ?? "Fill in the correct form for the word shown."}
              </p>
            </div>

            {endingsQuestion && (
              <div className="practice-card endings-card">
                <div className="practice-mirror">
                  <p className="subtitle">
                    {endingsQuestion.polish} ({endingsQuestion[languageSet]})
                    {endingsQuestion.case && <span className="context-tag">{endingsQuestion.case}</span>}
                    {endingsQuestion.tense && <span className="context-tag">{endingsQuestion.tense}</span>}
                    {endingsQuestion.pronoun && <span className="context-tag">{endingsQuestion.pronoun}</span>}
                    {endingsQuestion.gender && <span className="context-tag">{endingsQuestion.gender}</span>}
                  </p>
                  <p className="prompt endings-prompt">{endingsQuestion.sentence}</p>
                </div>

                {endingsMode === "choose" && (
                  <div className="endings-options">
                    {endingsQuestion.options.map((opt, i) => (
                      <button key={i} className="endings-option" onClick={() => handleEndingsAnswer(opt)}>{opt}</button>
                    ))}
                  </div>
                )}

                {endingsMode === "write" && (
                  <form onSubmit={(e) => { e.preventDefault(); handleEndingsAnswer(null); }} className="endings-write-form">
                    <input value={endingsWriteAnswer} onChange={(e) => setEndingsWriteAnswer(e.target.value)} placeholder="Type the correct form…" />
                    <button type="submit" disabled={!endingsWriteAnswer.trim()}>Submit</button>
                  </form>
                )}

                <button className="skip-btn endings-skip" onClick={handleEndingsSkip}>Skip</button>

                {/* Grammar reference toggle */}
                <button className="grammar-toggle" onClick={() => setShowGrammar(!showGrammar)} type="button">
                  {showGrammar ? "Hide grammar reference ▲" : "Show grammar reference ▼"}
                </button>
                {showGrammar && endingsQuestion.grammar_reference && (
                  <div className="grammar-panel">
                    {Object.entries(endingsQuestion.grammar_reference).map(([key, val]) => (
                      <div key={key} className="grammar-section">
                        <h4>{key}</h4>
                        {typeof val === "string" ? (
                          <p>{val}</p>
                        ) : typeof val === "object" && val !== null && Object.values(val).every(v => typeof v === "object" && v !== null && ("singular" in v || "plural" in v || "endings" in v)) ? (
                          /* Gender-based endings table: columns are genders, rows are singular/plural/examples */
                          <table className="grammar-table grammar-table-grid">
                            <thead>
                              <tr>
                                <th></th>
                                {Object.keys(val).map((gender) => (
                                  <th key={gender} className="grammar-gender-header">{gender}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {["singular", "plural", "examples"].map((row) => (
                                <tr key={row}>
                                  <td className="grammar-key">{row}</td>
                                  {Object.values(val).map((genderData, i) => (
                                    <td key={i}>{genderData[row] ?? "—"}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : typeof val === "object" && val !== null ? (
                          <table className="grammar-table">
                            <tbody>
                              {Object.entries(val).map(([k, v]) => (
                                <tr key={k}>
                                  <td className="grammar-key">{k}</td>
                                  <td>{typeof v === "object" ? JSON.stringify(v) : String(v)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : <p>{String(val)}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!endingsQuestion && (
              <div className="practice-card"><p>No words available for this practice type. Add some words first!</p></div>
            )}
          </section>
        )}

        {/* ── MANAGE ───────────────────────────────────── */}
        {activePage === "manage" && (
          <section className="panel">
            <div className="panel-header">
              <div><p className="subtitle">Manage</p><h2>Your word list</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>
            {allWords.length > 0 && (() => {
              const posTags = [...new Set(allWords.map((w) => w.part_of_speech || "inne"))].sort();
              return (
                <div className="filter-bar">
                  <span className="filter-label">Filter:</span>
                  <button className={`filter-chip ${manageFilterPoS.size === 0 ? "active" : ""}`} onClick={() => toggleManageFilter("all")}>All ({allWords.length})</button>
                  {posTags.map((tag) => {
                    const count = allWords.filter((w) => (w.part_of_speech || "inne") === tag).length;
                    return <button key={tag} className={`filter-chip ${manageFilterPoS.has(tag) ? "active" : ""}`} onClick={() => toggleManageFilter(tag)}>{tag} ({count})</button>;
                  })}
                </div>
              );
            })()}
            <div className="manage-list">
              {allWords.length === 0 ? (
                <p className="status info">No words in your session yet. Add some words first!</p>
              ) : (() => {
                const filtered = manageFilterPoS.size === 0 ? allWords : allWords.filter((w) => manageFilterPoS.has(w.part_of_speech || "inne"));
                return filtered.length === 0 ? (
                  <p className="status info">No words match this filter.</p>
                ) : (
                <ul className="word-manage-list">
                  {filtered.map((word) => (
                    <li key={word.id} className={`word-manage-item ${!word.enabled ? "disabled" : ""} ${editingWordId === word.id ? "editing" : ""}`}>
                      {editingWordId === word.id ? (
                        <div className="word-edit-form">
                          <div className="word-edit-fields">
                            <label className="word-edit-label">Polish<input className="word-edit-input" value={editingValues.polish} onChange={(e) => setEditingValues((v) => ({ ...v, polish: e.target.value }))} disabled={editSaving} /></label>
                            <label className="word-edit-label">English<input className="word-edit-input" value={editingValues.english} onChange={(e) => setEditingValues((v) => ({ ...v, english: e.target.value }))} disabled={editSaving} /></label>
                            <label className="word-edit-label">Ukrainian<input className="word-edit-input" value={editingValues.ukrainian} onChange={(e) => setEditingValues((v) => ({ ...v, ukrainian: e.target.value }))} disabled={editSaving} /></label>
                          </div>
                          <div className="word-edit-actions">
                            <button className="word-edit-save-btn" onClick={() => handleSaveEdit(word.id)} disabled={editSaving}>{editSaving ? "Saving…" : "Save"}</button>
                            <button className="word-edit-cancel-btn" onClick={handleCancelEdit} disabled={editSaving}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="word-info">
                            <span className="word-polish">{word.polish}</span>
                            <span className="pos-badge">{word.part_of_speech || "inne"}</span>
                            <span className="word-translation">{word[languageSet]}</span>
                          </div>
                          <div className="word-stats">{word.total_attempts > 0 ? `${word.error_rate}% errors (${word.total_attempts} tries)` : "New"}</div>
                          <button className="word-edit-btn" title="Edit translations" onClick={() => handleStartEditWord(word)}>✎</button>
                          <label className="toggle-switch">
                            <input type="checkbox" checked={word.enabled} onChange={(e) => handleToggleWord(word.id, e.target.checked)} />
                            <span className="toggle-slider"></span>
                          </label>
                          <button className="word-remove-btn" title="Delete word" onClick={() => handleDeleteWord(word.id)}>✕</button>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
                );
              })()}
            </div>
          </section>
        )}

        {/* ── ADMIN ──────────────────────────────────────── */}
        {activePage === "admin" && (
          <section className="panel admin-panel">
            <div className="panel-header">
              <div><p className="subtitle">Admin</p><h2>Connected Devices</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>
            <div className="admin-stats">
              <div className="admin-stat"><span className="stat-value">{deviceStats.total}</span><span className="stat-label">Total devices</span></div>
              <div className="admin-stat active"><span className="stat-value">{deviceStats.active}</span><span className="stat-label">Active now</span></div>
              <button className="secondary clear-btn" onClick={handleClearAllDevices}>Clear all</button>
            </div>
            <p className="admin-info">Updates every 5 seconds • Active = activity in last 5 minutes</p>
            <div className="devices-list">
              {connectedDevices.length === 0 ? (
                <p className="status info">No devices have connected yet.</p>
              ) : (
                <ul className="device-list">
                  {connectedDevices.map((device) => (
                    <li key={device.id} className={`device-item ${device.is_active ? "active" : "inactive"}`}>
                      <div className="device-status"><span className={`status-dot ${device.is_active ? "online" : "offline"}`}></span></div>
                      <div className="device-info">
                        <div className="device-primary"><span className="device-type">{device.device_type}</span><span className="device-browser">{device.browser} on {device.os}</span></div>
                        <div className="device-secondary"><span className="device-ip">{device.ip_address}</span><span className="device-requests">{device.request_count} requests</span></div>
                        <div className="device-times"><span>First seen: {new Date(device.first_seen).toLocaleString()}</span><span>Last active: {new Date(device.last_activity).toLocaleString()}</span></div>
                      </div>
                      <button className="device-remove-btn" title="Remove device" onClick={() => handleDeleteDevice(device.id)}>✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Settings */}
            <div className="admin-section">
              <h3>Settings</h3>
              <div className="admin-toggle-row">
                <span>On-the-fly sentence generation (Endings)</span>
                <label className="toggle-switch">
                  <input type="checkbox" checked={generateOnTheFly} onChange={toggleOnTheFly} />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              <p className="admin-info">When enabled, new sentences are generated via LLM during practice and saved for future use.</p>
              <div className="admin-toggle-row">
                <span>Pronunciation TTS: {ttsSource === "server" ? "Server (OpenAI)" : "Browser"}</span>
                <label className="toggle-switch">
                  <input type="checkbox" checked={ttsSource === "server"} onChange={toggleTtsSource} />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              <p className="admin-info">Browser uses device voices (free). Server uses OpenAI TTS (higher quality, costs API credits).</p>
            </div>

            {/* Sentence Management */}
            <div className="admin-section">
              <h3>Practice Sentences ({sentences.length})</h3>
              {sentences.length > 0 && (() => {
                const posTags = [...new Set(sentences.map((s) => s.part_of_speech))].sort();
                const metaTags = [...new Set(sentences.flatMap((s) => [s.case, s.tense].filter(Boolean)))].sort();
                const filtered = sentences.filter((s) => {
                  if (sentenceFilterPoS.size > 0 && !sentenceFilterPoS.has(s.part_of_speech)) return false;
                  if (sentenceFilterMeta.size > 0 && !sentenceFilterMeta.has(s.case) && !sentenceFilterMeta.has(s.tense)) return false;
                  return true;
                });
                return (
                  <>
                    <div className="filter-bar">
                      <span className="filter-label">Type:</span>
                      <button className={`filter-chip ${sentenceFilterPoS.size === 0 ? "active" : ""}`} onClick={() => toggleSentencePoS("all")}>All</button>
                      {posTags.map((tag) => <button key={tag} className={`filter-chip ${sentenceFilterPoS.has(tag) ? "active" : ""}`} onClick={() => toggleSentencePoS(tag)}>{tag}</button>)}
                    </div>
                    {metaTags.length > 0 && (
                      <div className="filter-bar">
                        <span className="filter-label">Case/Tense:</span>
                        <button className={`filter-chip ${sentenceFilterMeta.size === 0 ? "active" : ""}`} onClick={() => toggleSentenceMeta("all")}>All</button>
                        {metaTags.map((tag) => <button key={tag} className={`filter-chip ${sentenceFilterMeta.has(tag) ? "active" : ""}`} onClick={() => toggleSentenceMeta(tag)}>{tag}</button>)}
                      </div>
                    )}
                    <p className="filter-count">{filtered.length} of {sentences.length} sentences</p>
                    {filtered.length === 0 ? (
                      <p className="status info">No sentences match filters.</p>
                    ) : (
                    <ul className="sentence-list">
                      {filtered.map((s) => (
                    <li key={s.id} className="sentence-item">
                      {editingSentenceId === s.id ? (
                        <div className="sentence-edit-form">
                          <label className="sentence-edit-label">Sentence
                            <input className="sentence-edit-input" value={editingSentenceValues.sentence} onChange={(e) => setEditingSentenceValues((v) => ({ ...v, sentence: e.target.value }))} />
                          </label>
                          <label className="sentence-edit-label">Correct answer
                            <input className="sentence-edit-input" value={editingSentenceValues.correct_answer} onChange={(e) => setEditingSentenceValues((v) => ({ ...v, correct_answer: e.target.value }))} />
                          </label>
                          <div className="sentence-edit-actions">
                            <button onClick={() => handleSaveSentence(s.id)}>Save</button>
                            <button className="secondary" onClick={() => setEditingSentenceId(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="sentence-info">
                            <span className="sentence-word">{s.word_polish}</span>
                            <span className="pos-badge">{s.part_of_speech}</span>
                            {s.case && <span className="sentence-meta">{s.case}</span>}
                            {s.tense && <span className="sentence-meta">{s.tense}</span>}
                            {s.pronoun && <span className="sentence-meta">{s.pronoun}</span>}
                          </div>
                          <div className="sentence-text">{s.sentence}</div>
                          <div className="sentence-answer">Answer: <strong>{s.correct_answer}</strong></div>
                          <div className="sentence-actions">
                            <button className="sentence-edit-btn" title="Edit" onClick={() => { setEditingSentenceId(s.id); setEditingSentenceValues({ sentence: s.sentence, correct_answer: s.correct_answer }); }}>✎</button>
                            <button className="sentence-fix-btn" title="Fix with LLM" disabled={sentenceFixingId === s.id} onClick={() => handleFixSentence(s.id)}>{sentenceFixingId === s.id ? <span className="spinner" /> : "🔧"}</button>
                            <button className="sentence-delete-btn" title="Delete" onClick={() => handleDeleteSentence(s.id)}>✕</button>
                          </div>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
                    )}
                  </>
                );
              })()}
              {sentences.length === 0 && (
                <p className="status info">No sentences yet. They are generated when adding words or during on-the-fly practice.</p>
              )}
            </div>
          </section>
        )}

        {/* ── STATS DETAIL ─────────────────────────────── */}
        {activePage === "stats-detail" && (
          <section className="panel stats-detail-panel">
            <div className="panel-header">
              <div><p className="subtitle">Statistics</p><h2>Detailed History</h2></div>
              <button className="secondary" onClick={() => setActivePage("home")}>Back to main</button>
            </div>

            <div className="stats-summary-row">
              <div className="stats-summary-item">
                <span className="stats-summary-label">Today</span>
                <span className="stats-summary-value">{statsSummary.today}</span>
              </div>
              <div className="stats-summary-item">
                <span className="stats-summary-label">Trend</span>
                <span className="stats-summary-value">{statsSummary.trend}</span>
              </div>
              <div className="stats-summary-item">
                <span className="stats-summary-label">Overall</span>
                <span className="stats-summary-value">{statsSummary.overall}</span>
              </div>
              <div className="stats-summary-item">
                <span className="stats-summary-label">Total answers</span>
                <span className="stats-summary-value">{historyTotal}</span>
              </div>
            </div>

            {historyLoading && <p className="status info">Loading history…</p>}

            {!historyLoading && historyRecords.length === 0 && (
              <p className="status info">No practice history yet. Start practicing!</p>
            )}

            {!historyLoading && historyRecords.length > 0 && (
              <ul className="history-list">
                {historyRecords.map((rec) => (
                  <li key={rec.id} className={`history-item ${rec.was_correct ? "correct" : "incorrect"}`}>
                    <div className="history-item-main">
                      <span className={`history-dot ${rec.was_correct ? "correct" : "incorrect"}`} />
                      <div className="history-item-info">
                        <span className="history-word">{rec.word_polish}</span>
                        <span className="history-translation">{rec.word_translation}</span>
                      </div>
                      <span className="history-section-badge">{rec.section}</span>
                      <div className="history-answer-info">
                        {rec.user_answer && <span className="history-user-answer">You: {rec.user_answer}</span>}
                        {rec.correct_answer && <span className="history-correct-answer">Answer: {rec.correct_answer}</span>}
                      </div>
                      <span className="history-time">{new Date(rec.created_at).toLocaleString()}</span>
                      <button
                        className="history-explain-btn"
                        onClick={() => expandedExplain === rec.id ? setExpandedExplain(null) : fetchExplain(rec)}
                        type="button"
                      >
                        {expandedExplain === rec.id ? "Hide" : "Explain"}
                      </button>
                    </div>
                    {expandedExplain === rec.id && (
                      <div className="history-explain-panel">
                        {explainLoading ? <p className="status info">Generating explanation…</p> : <p>{explainText}</p>}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;