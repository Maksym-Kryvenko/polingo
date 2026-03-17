import { useEffect, useMemo, useState, useRef, useCallback } from "react";

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
  if (hash === "admin") return "admin";
  return "home";
}

function App() {
  const [activePage, setActivePage] = useState(getInitialPage);
  const [languageSet, setLanguageSet] = useState("english");
  const [manualEntry, setManualEntry] = useState("");
  const [manualStatus, setManualStatus] = useState(null);
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

  // Admin state
  const [connectedDevices, setConnectedDevices] = useState([]);
  const [deviceStats, setDeviceStats] = useState({ total: 0, active: 0 });
  const adminPollIntervalRef = useRef(null);

  // ── Fetch helpers ─────────────────────────────────────────
  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const r = await fetch(buildUrl("stats"));
      if (r.ok) setStats(await r.json());
    } catch (e) { console.error(e); }
    finally { setLoadingStats(false); }
  };

  const fetchSession = async () => {
    try {
      const r = await fetch(buildUrl("session"));
      if (r.ok) {
        const data = await r.json();
        setLanguageSet(data.language_set);
        setWordPool(data.words ?? []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchAllWords = async () => {
    try {
      const r = await fetch(buildUrl("session/words/all"));
      if (r.ok) {
        const data = await r.json();
        setAllWords(data.words ?? []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchEndingsConfig = async () => {
    try {
      const r = await fetch(buildUrl("endings/config"));
      if (r.ok) setEndingsConfig(await r.json());
    } catch (e) { console.error(e); }
  };

  const fetchEndingsQuestion = async () => {
    try {
      const params = new URLSearchParams({ part_of_speech: endingsPoS });
      if (endingsPoS === "czasownik") {
        params.set("tenses", endingsTenses.join(","));
      } else {
        params.set("cases", endingsCases.join(","));
      }
      const r = await fetch(buildUrl(`endings/question?${params}`));
      if (r.ok) setEndingsQuestion(await r.json());
      else setEndingsQuestion(null);
    } catch (e) { console.error(e); setEndingsQuestion(null); }
  };

  const fetchEndingsStats = async () => {
    try {
      const r = await fetch(buildUrl("endings/stats"));
      if (r.ok) setEndingsStats(await r.json());
    } catch (e) { console.error(e); }
  };

  const fetchChooseQuestion = async () => {
    try {
      const r = await fetch(buildUrl(`practice/choose-translation/question?language_set=${languageSet}&direction=${practiceDirection}`));
      if (r.ok) setChooseQuestion(await r.json());
      else setChooseQuestion(null);
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

  // ── Effects ───────────────────────────────────────────────
  useEffect(() => { fetchStats(); fetchSession(); fetchEndingsConfig(); }, []);

  useEffect(() => {
    if (activePage === "manage") fetchAllWords();
    if (activePage === "admin") {
      fetchConnectedDevices();
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
    try { await fetch(buildUrl("session/language"), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ language_set: value }) }); } catch (e) { console.error(e); }
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
    finally { setManualEntry(""); }
  };

  const handlePracticeSubmit = async (event) => {
    event?.preventDefault?.();
    if (!currentWriteTranslateWord) return;
    if (practiceStatusTimeoutRef.current) clearTimeout(practiceStatusTimeoutRef.current);
    if (!answer.trim()) { setPracticeStatus({ type: "error", message: "Try answering first." }); return; }
    const dir = practiceMode === "writing" ? "writing" : "translation";
    try {
      const r = await fetch(buildUrl("practice/validate"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: currentWriteTranslateWord.id, language_set: languageSet, direction: dir, answer }) });
      if (!r.ok) throw new Error();
      const p = await r.json();
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
      const r = await fetch(buildUrl("practice/skip"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: currentWriteTranslateWord.id, language_set: languageSet, direction: dir, answer: "" }) });
      if (!r.ok) throw new Error();
      const p = await r.json();
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
      const r = await fetch(buildUrl("practice/choose-translation/validate"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: chooseQuestion.word_id, language_set: languageSet, direction: practiceDirection, answer: selected }) });
      if (!r.ok) throw new Error();
      const p = await r.json();
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
      await fetch(buildUrl("practice/choose-translation/validate"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: chooseQuestion.word_id, language_set: languageSet, direction: practiceDirection, answer: "" }) });
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
      const r = await fetch(buildUrl("practice/pronunciation"), { method: "POST", body: fd });
      if (!r.ok) throw new Error();
      const p = await r.json();
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
      const r = await fetch(buildUrl("practice/skip"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: currentPronunciationWord.id, language_set: languageSet, direction: "pronunciation", answer: "" }) });
      if (r.ok) { const p = await r.json(); setStats(p.stats); }
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
      const r = await fetch(buildUrl("endings/validate"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: endingsQuestion.word_id, answer: answerText, correct_answer: endingsQuestion.correct_answer }) });
      if (!r.ok) throw new Error();
      const p = await r.json();
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
      await fetch(buildUrl("endings/validate"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word_id: endingsQuestion.word_id, answer: "", correct_answer: endingsQuestion.correct_answer }) });
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
        <div className="stats-card">
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
              <button onClick={handleManualSubmit}>Validate &amp; add</button>
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
                  <p className="prompt">{practiceMode === "writing" ? (writingPrompt ?? "Add words to start.") : (translationPrompt ?? "Add words to start.")}</p>
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
                      <p className="prompt choose-translation-prompt">{chooseQuestion.prompt}</p>
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

            {/* Config panel */}
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

            {endingsStats && (
              <div className="endings-stats">
                <span>Today: {endingsStats.today_percentage}%</span>
                <span>Overall: {endingsStats.overall_percentage}%</span>
                <span>Words: {endingsStats.available_words}</span>
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
            <div className="manage-list">
              {allWords.length === 0 ? (
                <p className="status info">No words in your session yet. Add some words first!</p>
              ) : (
                <ul className="word-manage-list">
                  {allWords.map((word) => (
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
              )}
            </div>
          </section>
        )}

        {/* ── ADMIN ────────────────────────────────────── */}
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
          </section>
        )}
      </main>
    </div>
  );
}

export default App;