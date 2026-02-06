import { useEffect, useMemo, useState, useRef, useCallback } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

// Fisher-Yates shuffle algorithm
function shuffleArray(array) {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Helper to render text with incorrect characters highlighted
function renderSpellingDiff(userAnswer, correctAnswer) {
  const result = [];
  const maxLen = Math.max(userAnswer.length, correctAnswer.length);
  
  for (let i = 0; i < maxLen; i++) {
    const userChar = userAnswer[i] || '';
    const correctChar = correctAnswer[i] || '';
    
    if (userChar.toLowerCase() !== correctChar.toLowerCase()) {
      if (userChar) {
        result.push(<span key={i} className="char-incorrect">{userChar}</span>);
      }
      if (!userAnswer[i] && correctChar) {
        result.push(<span key={`missing-${i}`} className="char-missing">{correctChar}</span>);
      }
    } else {
      result.push(<span key={i} className="char-correct">{userChar}</span>);
    }
  }
  
  return result;
}
const LANGUAGE_LABELS = {
  english: "English",
  ukrainian: "Ukrainian",
};
const FIELD_LABELS = {
  polish: "Polish entry",
  english: "English entry",
  ukrainian: "Ukrainian entry",
  resolved: "LLM match",
};

const buildUrl = (path) => `${API_BASE_URL}/${path}`;

// Auto-hide delay in milliseconds
const STATUS_HIDE_DELAY = 5000;

function App() {
  const [activePage, setActivePage] = useState("home");
  const [languageSet, setLanguageSet] = useState("english");
  const [manualEntry, setManualEntry] = useState("");
  const [manualStatus, setManualStatus] = useState(null);
  const [wordPool, setWordPool] = useState([]);
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [practiceStatus, setPracticeStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [shuffledWords, setShuffledWords] = useState([]);
  const [lastAnswer, setLastAnswer] = useState(null); // { userAnswer, correctAnswer, alternatives, wasCorrect }
  
  // Pronunciation state
  const [isRecording, setIsRecording] = useState(false);
  const [pronunciationStatus, setPronunciationStatus] = useState(null);
  const [pronunciationIndex, setPronunciationIndex] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Timeout refs for auto-hiding status messages
  const practiceStatusTimeoutRef = useRef(null);
  const pronunciationStatusTimeoutRef = useRef(null);
  const endingsStatusTimeoutRef = useRef(null);

  // Add words mode selector (words vs verbs)
  const [addMode, setAddMode] = useState("words"); // "words" or "verbs"
  
  // Endings/Verbs state
  const [verbPool, setVerbPool] = useState([]);
  const [endingsQuestion, setEndingsQuestion] = useState(null);
  const [endingsStatus, setEndingsStatus] = useState(null);
  const [endingsStats, setEndingsStats] = useState(null);
  const [verbEntry, setVerbEntry] = useState("");
  const [verbStatus, setVerbStatus] = useState(null);
  const [verbLoading, setVerbLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchSession();
    fetchVerbSession();
    fetchEndingsStats();
  }, []);

  useEffect(() => {
    if (!wordPool.length) {
      setPracticeIndex(0);
    }
  }, [wordPool.length]);

  useEffect(() => {
    setAnswer("");
    setPracticeStatus(null);
    setPracticeIndex(0);
    setPronunciationStatus(null);
    setPronunciationIndex(0);
    setEndingsStatus(null);
    setEndingsQuestion(null);
    setLastAnswer(null);
    
    // Shuffle words when entering any practice mode
    if (activePage === "translation" || activePage === "writing" || activePage === "pronunciation") {
      setShuffledWords(shuffleArray(wordPool));
    }
    
    // Fetch first endings question when entering endings mode
    if (activePage === "endings") {
      fetchEndingsQuestion();
    }
  }, [activePage, languageSet, wordPool]);

  const practiceDirection =
    activePage === "translation" ? "translation" : activePage === "writing" ? "writing" : null;
  const currentWord =
    practiceDirection && shuffledWords.length ? shuffledWords[practiceIndex % shuffledWords.length] : null;
  const currentPronunciationWord =
    activePage === "pronunciation" && shuffledWords.length ? shuffledWords[pronunciationIndex % shuffledWords.length] : null;
  const targetLabel = LANGUAGE_LABELS[languageSet];
  const prompt =
    practiceDirection === "translation" ? currentWord?.polish : currentWord?.[languageSet];

  const statsSummary = useMemo(() => {
    if (!stats) {
      return { today: "--", trend: "--", overall: "--" };
    }
    const trend = stats.trend >= 0 ? `+${stats.trend}` : `${stats.trend}`;
    return {
      today: `${stats.today_percentage}%`,
      trend: `${trend}%`,
      overall: `${stats.overall_percentage}%`,
      availableWords: stats.available_words,
    };
  }, [stats]);

  const readinessBar = useMemo(() => {
    const capacity = wordPool.length / 20;
    return `${Math.min(100, Math.round(capacity * 100))}%`;
  }, [wordPool.length]);

  const dictionarySize = statsSummary.availableWords ?? "--";

  async function fetchStats() {
    setLoadingStats(true);
    try {
      const response = await fetch(buildUrl("stats"));
      if (!response.ok) {
        throw new Error("Stats fetch failed");
      }
      setStats(await response.json());
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingStats(false);
    }
  }

  async function fetchSession() {
    try {
      const response = await fetch(buildUrl("session"));
      if (!response.ok) {
        throw new Error("Session fetch failed");
      }
      const payload = await response.json();
      setLanguageSet(payload.language_set);
      setWordPool(payload.words ?? []);
    } catch (error) {
      console.error(error);
    }
  }

  async function fetchVerbSession() {
    try {
      const response = await fetch(buildUrl("verbs/session"));
      if (!response.ok) {
        throw new Error("Verb session fetch failed");
      }
      const payload = await response.json();
      setVerbPool(payload.verbs ?? []);
    } catch (error) {
      console.error(error);
    }
  }

  async function fetchEndingsStats() {
    try {
      const response = await fetch(buildUrl("verbs/stats"));
      if (response.ok) {
        setEndingsStats(await response.json());
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function fetchEndingsQuestion() {
    try {
      const response = await fetch(buildUrl("verbs/question"));
      if (!response.ok) {
        throw new Error("Could not get question");
      }
      const payload = await response.json();
      setEndingsQuestion(payload);
    } catch (error) {
      console.error(error);
      setEndingsStatus({ type: "error", message: "Add verbs to your session first." });
    }
  }

  const handleLanguageChange = async (value) => {
    setLanguageSet(value);
    try {
      await fetch(buildUrl("session/language"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language_set: value }),
      });
    } catch (error) {
      console.error(error);
    }
  };

  const handleLoadInitial = async () => {
    try {
      const response = await fetch(buildUrl("words/initial?count=10"));
      if (!response.ok) {
        throw new Error("Unable to load starter set");
      }
      const payload = await response.json();
      const saved = await fetch(buildUrl("session/words/bulk"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word_ids: payload.map((word) => word.id) }),
      });
      if (!saved.ok) {
        throw new Error("Unable to persist starter set");
      }
      const sessionState = await saved.json();
      setWordPool(sessionState.words ?? []);
      setManualStatus({ type: "success", message: "Loaded and saved the first 10 words." });
    } catch (error) {
      console.error(error);
      setManualStatus({ type: "error", message: "Could not reach the starter set. Try again." });
    }
  };

  const handleManualSubmit = async () => {
    const trimmed = manualEntry.trim();
    if (!trimmed) {
      setManualStatus({ type: "error", message: "Type a word or phrase to validate it." });
      return;
    }

    // Check if input contains commas (bulk input)
    const hasBulkInput = trimmed.includes(",");

    try {
      if (hasBulkInput) {
        // Bulk word check
        const response = await fetch(buildUrl("words/check/bulk"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: trimmed }),
        });

        if (!response.ok) {
          throw new Error("Bulk validation failed");
        }

        const payload = await response.json();
        
        // Refresh session to get updated word list with stats
        await fetchSession();
        
        const messages = [];
        if (payload.added_count > 0) {
          messages.push(`Added ${payload.added_count} word(s)`);
        }
        if (payload.duplicate_count > 0) {
          messages.push(`${payload.duplicate_count} already in session`);
        }
        if (payload.failed_count > 0) {
          messages.push(`${payload.failed_count} could not be found`);
        }
        
        const hasSuccess = payload.added_count > 0;
        setManualStatus({
          type: hasSuccess ? "success" : (payload.duplicate_count > 0 ? "info" : "error"),
          message: messages.join(". ") + ".",
        });
      } else {
        // Single word check (existing logic)
        const response = await fetch(buildUrl("words/check"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: trimmed }),
        });

        if (!response.ok) {
          throw new Error("Validation failed");
        }

        const payload = await response.json();
        if (!payload.found || !payload.word) {
          setManualStatus({
            type: "error",
            message: "Word not found. Please double-check spelling or try a different form.",
          });
          return;
        }

        const saved = await fetch(buildUrl("session/words"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ word_id: payload.word.id }),
        });
        if (!saved.ok) {
          throw new Error("Unable to save word to session");
        }
        const sessionState = await saved.json();
        setWordPool(sessionState.words ?? []);
        const sourceLabel = FIELD_LABELS[payload.matched_field] ?? "entry";
        const extra = payload.created ? "Added via GPT validation." : "";
        setManualStatus({
          type: "success",
          message: `Saved ${payload.word.polish} (${sourceLabel}). ${extra}`.trim(),
        });
      }
    } catch (error) {
      console.error(error);
      setManualStatus({
        type: "error",
        message: "Something went wrong talking to the database. Try again in a moment.",
      });
    } finally {
      setManualEntry("");
    }
  };

  const handleVerbSubmit = async () => {
    const trimmed = verbEntry.trim();
    if (!trimmed) {
      setVerbStatus({ type: "error", message: "Type a verb to add." });
      return;
    }

    setVerbLoading(true);
    try {
      const response = await fetch(buildUrl("verbs/add"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, source_language: languageSet }),
      });

      if (!response.ok) {
        throw new Error("Verb addition failed");
      }

      const payload = await response.json();
      
      if (!payload.success) {
        setVerbStatus({ type: "error", message: payload.message });
        return;
      }

      // Add to session if not duplicate
      if (!payload.duplicate && payload.verb) {
        await fetch(buildUrl(`verbs/session?verb_id=${payload.verb.id}`), {
          method: "POST",
        });
      } else if (payload.verb) {
        // Even if duplicate, add to session
        await fetch(buildUrl(`verbs/session?verb_id=${payload.verb.id}`), {
          method: "POST",
        });
      }

      await fetchVerbSession();
      
      const conjugationList = payload.verb?.conjugations
        ?.map(c => `${c.pronoun}: ${c.conjugated_form}`)
        ?.join(", ");
      
      setVerbStatus({
        type: payload.duplicate ? "info" : "success",
        message: `${payload.message} (${conjugationList})`,
      });
    } catch (error) {
      console.error(error);
      setVerbStatus({
        type: "error",
        message: "Could not add verb. Try again.",
      });
    } finally {
      setVerbEntry("");
      setVerbLoading(false);
    }
  };

  const handleEndingsAnswer = async (selectedAnswer) => {
    if (!endingsQuestion) return;

    // Clear any existing timeout
    if (endingsStatusTimeoutRef.current) {
      clearTimeout(endingsStatusTimeoutRef.current);
    }

    try {
      const response = await fetch(buildUrl("verbs/validate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verb_id: endingsQuestion.verb_id,
          pronoun: endingsQuestion.pronoun,
          answer: selectedAnswer,
        }),
      });

      if (!response.ok) {
        throw new Error("Validation failed");
      }

      const payload = await response.json();
      
      if (payload.was_correct) {
        setEndingsStatus({ type: "success", message: "Correct! Well done." });
      } else {
        setEndingsStatus({
          type: "error",
          message: `Incorrect. The answer was "${payload.correct_answer}".`,
        });
      }
      
      setEndingsStats(payload.stats);
      
      // Fetch next question immediately
      fetchEndingsQuestion();
      
      // Auto-hide feedback after delay
      endingsStatusTimeoutRef.current = setTimeout(() => {
        setEndingsStatus(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
      setEndingsStatus({ type: "error", message: "Could not validate answer." });
    }
  };

  const handleEndingsSkip = async () => {
    if (!endingsQuestion) return;

    // Clear any existing timeout
    if (endingsStatusTimeoutRef.current) {
      clearTimeout(endingsStatusTimeoutRef.current);
    }

    try {
      // Record as incorrect
      await fetch(buildUrl("verbs/validate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verb_id: endingsQuestion.verb_id,
          pronoun: endingsQuestion.pronoun,
          answer: "", // Empty = wrong
        }),
      });
      
      setEndingsStatus({
        type: "info",
        message: `Skipped. The answer was "${endingsQuestion.correct_answer}".`,
      });
      
      await fetchEndingsStats();
      
      // Fetch next question immediately
      fetchEndingsQuestion();
      
      // Auto-hide feedback after delay
      endingsStatusTimeoutRef.current = setTimeout(() => {
        setEndingsStatus(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
    }
  };

  const handlePracticeSubmit = async (event) => {
    event?.preventDefault?.();
    if (!currentWord || !practiceDirection) {
      return;
    }

    // Clear any existing timeout
    if (practiceStatusTimeoutRef.current) {
      clearTimeout(practiceStatusTimeoutRef.current);
    }

    if (!answer.trim()) {
      setPracticeStatus({ type: "error", message: "Try answering before submitting." });
      return;
    }

    try {
      const response = await fetch(buildUrl("practice/validate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word_id: currentWord.id,
          language_set: languageSet,
          direction: practiceDirection,
          answer,
        }),
      });

      if (!response.ok) {
        throw new Error("Practice validation failed");
      }

      const payload = await response.json();
      const baseMessage = payload.was_correct
        ? "Correct! Keep going."
        : `The correct answer is “${payload.correct_answer}”.`;
      setPracticeStatus({ type: payload.was_correct ? "success" : "error", message: baseMessage });
      setStats(payload.stats);
      
      // Store answer details for display
      setLastAnswer({
        userAnswer: answer,
        correctAnswer: payload.correct_answer,
        alternatives: payload.alternatives || [],
        wasCorrect: payload.was_correct,
        direction: practiceDirection,
        skipped: false,
      });
      
      // Auto-hide after 5 seconds
      practiceStatusTimeoutRef.current = setTimeout(() => {
        setPracticeStatus(null);
        setLastAnswer(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
      setPracticeStatus({
        type: "error",
        message: "Progress could not be recorded. Try again.",
      });
    }
    setAnswer("");
    setPracticeIndex((previous) => (previous + 1) % wordPool.length);
  };

  const handleSkip = async () => {
    if (!currentWord || !practiceDirection) {
      return;
    }

    // Clear any existing timeout
    if (practiceStatusTimeoutRef.current) {
      clearTimeout(practiceStatusTimeoutRef.current);
    }

    try {
      const response = await fetch(buildUrl("practice/skip"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word_id: currentWord.id,
          language_set: languageSet,
          direction: practiceDirection,
          answer: "",
        }),
      });

      if (!response.ok) {
        throw new Error("Skip failed");
      }

      const payload = await response.json();
      
      setLastAnswer({
        userAnswer: "",
        correctAnswer: payload.correct_answer,
        alternatives: payload.alternatives || [],
        wasCorrect: false,
        direction: practiceDirection,
        skipped: true,
      });
      
      setPracticeStatus({ type: "info", message: "Skipped. The answer was:" });
      setStats(payload.stats);
      
      // Auto-hide after 5 seconds
      practiceStatusTimeoutRef.current = setTimeout(() => {
        setPracticeStatus(null);
        setLastAnswer(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
      setPracticeStatus({
        type: "error",
        message: "Could not skip. Try again.",
      });
    }
    setAnswer("");
    setPracticeIndex((previous) => (previous + 1) % shuffledWords.length);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await submitPronunciation(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setPronunciationStatus({ type: "info", message: "Recording... Click Stop when done." });
    } catch (error) {
      console.error(error);
      setPronunciationStatus({
        type: "error",
        message: "Could not access microphone. Please allow microphone access and try again.",
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setPronunciationStatus({ type: "info", message: "Processing your pronunciation..." });
    }
  };

  const submitPronunciation = async (audioBlob) => {
    if (!currentPronunciationWord) return;

    // Clear any existing timeout
    if (pronunciationStatusTimeoutRef.current) {
      clearTimeout(pronunciationStatusTimeoutRef.current);
    }

    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("word_id", currentPronunciationWord.id);
    formData.append("language_set", languageSet);

    try {
      const response = await fetch(buildUrl("practice/pronunciation"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Pronunciation validation failed");
      }

      const payload = await response.json();
      const scorePercent = Math.round(payload.similarity_score * 100);
      
      if (payload.was_correct) {
        setPronunciationStatus({
          type: "success",
          message: `Correct! You said "${payload.transcribed_text}" (${scorePercent}% match)`,
        });
      } else {
        setPronunciationStatus({
          type: "error",
          message: `You said "${payload.transcribed_text}". Expected "${payload.expected_word}". ${payload.feedback}`,
        });
      }
      setStats(payload.stats);
      
      // Auto-hide after 5 seconds
      pronunciationStatusTimeoutRef.current = setTimeout(() => {
        setPronunciationStatus(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
      setPronunciationStatus({
        type: "error",
        message: "Could not validate pronunciation. Please try again.",
      });
    }
  };

  const nextPronunciationWord = () => {
    setPronunciationIndex((prev) => (prev + 1) % shuffledWords.length);
    setPronunciationStatus(null);
  };

  const handlePronunciationSkip = async () => {
    if (!currentPronunciationWord) return;
    
    // Clear any existing timeout
    if (pronunciationStatusTimeoutRef.current) {
      clearTimeout(pronunciationStatusTimeoutRef.current);
    }
    
    try {
      const response = await fetch(buildUrl("practice/skip"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word_id: currentPronunciationWord.id,
          language_set: languageSet,
          direction: "pronunciation",
          answer: "",
        }),
      });
      
      if (response.ok) {
        const payload = await response.json();
        setStats(payload.stats);
      }
      
      setPronunciationStatus({ 
        type: "info", 
        message: `Skipped. The word was "${currentPronunciationWord.polish}".` 
      });
      
      // Auto-hide after 5 seconds
      pronunciationStatusTimeoutRef.current = setTimeout(() => {
        setPronunciationStatus(null);
      }, STATUS_HIDE_DELAY);
    } catch (error) {
      console.error(error);
    }
    
    setPronunciationIndex((prev) => (prev + 1) % shuffledWords.length);
  };

  const renderPracticePage = (directionLabel) => (
    <section className="panel practice-panel">
      <div className="panel-header">
        <div>
          <p className="subtitle">Practice</p>
          <h2>{directionLabel} mode</h2>
        </div>
        <button className="secondary" onClick={() => setActivePage("home")}>
          Back to main
        </button>
      </div>

      {!shuffledWords.length && (
        <p className="status info">
          Add words to your session first, then return here to practice.
        </p>
      )}

      <div className="practice-status">
        <p className={`status ${practiceStatus?.type ?? "info"}`}>
          {practiceStatus?.message ?? "Practice results appear here after each submission."}
        </p>
        
        {/* Show answer details with spelling highlight for writing mode */}
        {lastAnswer && !lastAnswer.wasCorrect && (
          <div className="answer-details">
            {lastAnswer.direction === "writing" && lastAnswer.userAnswer && !lastAnswer.skipped && (
              <p className="spelling-diff">
                Your answer: {renderSpellingDiff(lastAnswer.userAnswer, lastAnswer.correctAnswer)}
              </p>
            )}
            <p className="correct-answer">
              Correct: <strong>{lastAnswer.correctAnswer}</strong>
            </p>
            {lastAnswer.alternatives.length > 0 && (
              <p className="alternatives">
                Also accepted: {lastAnswer.alternatives.join(", ")}
              </p>
            )}
          </div>
        )}
        
        {/* Show alternatives even for correct answers */}
        {lastAnswer && lastAnswer.wasCorrect && lastAnswer.alternatives.length > 0 && (
          <div className="answer-details">
            <p className="alternatives">
              Other accepted answers: {lastAnswer.alternatives.join(", ")}
            </p>
          </div>
        )}
      </div>

      <form onSubmit={handlePracticeSubmit} className="practice-card">
        <div className="practice-mirror">
          <p className="subtitle">Target language: {targetLabel}</p>
          <p className="prompt">
            {prompt ?? "Add words and return here to start practicing."}
          </p>
        </div>
        <input
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          placeholder={
            practiceDirection === "translation"
              ? `Type the ${targetLabel} translation...`
              : "Type the Polish word..."
          }
          disabled={!practiceDirection || !currentWord}
        />
        <div className="practice-buttons">
          <button type="submit" disabled={!practiceDirection || !currentWord}>
            Submit answer
          </button>
          <button 
            type="button" 
            className="skip-btn"
            onClick={handleSkip} 
            disabled={!practiceDirection || !currentWord}
          >
            Skip
          </button>
        </div>
      </form>
    </section>
  );

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Polingo</p>
          <h1>Polish practice that respects your tempo</h1>
          <p className="lede">
            Your session is saved automatically. Add words, practice translations, and come back later
            without losing your progress.
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
        {activePage === "home" && (
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="subtitle">Session control</p>
                <select
                  value={languageSet}
                  onChange={(event) => handleLanguageChange(event.target.value)}
                  className="language-select"
                >
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

            <div className="progress-track">
              <span style={{ width: readinessBar }} />
            </div>

            <div className="nav-grid">
              <button className="nav-card" onClick={() => setActivePage("add")}
                type="button">
                <p className="subtitle">Add words</p>
                <h3>Build your session list</h3>
                <p>Validate new entries or load the starter set.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("translation")}
                type="button">
                <p className="subtitle">Translation</p>
                <h3>Translate Polish prompts</h3>
                <p>Check yourself in English or Ukrainian.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("writing")}
                type="button">
                <p className="subtitle">Writing</p>
                <h3>Write Polish words</h3>
                <p>Recall the Polish form from translation.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("pronunciation")}
                type="button">
                <p className="subtitle">Pronunciation</p>
                <h3>Speak Polish words</h3>
                <p>Practice saying words and get AI feedback.</p>
              </button>
              <button className="nav-card" onClick={() => setActivePage("endings")}
                type="button">
                <p className="subtitle">Endings</p>
                <h3>Practice verb conjugations</h3>
                <p>Learn how verbs change with ja, ty, on/ona, my, wy, oni.</p>
              </button>
            </div>
          </section>
        )}

        {activePage === "add" && (
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="subtitle">Add words</p>
                <h2>Curate your session list</h2>
              </div>
              <button className="secondary" onClick={() => setActivePage("home")}>
                Back to main
              </button>
            </div>

            {/* Mode selector tabs */}
            <div className="mode-tabs">
              <button 
                className={`mode-tab ${addMode === "words" ? "active" : ""}`}
                onClick={() => setAddMode("words")}
                type="button"
              >
                Words
              </button>
              <button 
                className={`mode-tab ${addMode === "verbs" ? "active" : ""}`}
                onClick={() => setAddMode("verbs")}
                type="button"
              >
                Verbs (Endings)
              </button>
            </div>

            {addMode === "words" && (
              <>
                <div className="instruction-card">
                  <p className="step">1</p>
                  <div>
                    <p className="instruction-title">Validate new words</p>
                    <p className="instruction-body">
                      Enter a single word or multiple words separated by commas. Duplicates are automatically skipped.
                    </p>
                  </div>
                </div>

                <div className="manual-entry">
                  <input
                    value={manualEntry}
                    onChange={(event) => setManualEntry(event.target.value)}
                    type="text"
                    placeholder="Type words (e.g., hello, goodbye, thank you)"
                  />
                  <button onClick={handleManualSubmit}>Validate &amp; add</button>
                </div>
                {manualStatus && <p className={`status ${manualStatus.type}`}>{manualStatus.message}</p>}

                <div className="instruction-card">
                  <p className="step">2</p>
                  <div>
                    <p className="instruction-title">Or load the starter list</p>
                    <p className="instruction-body">
                      These first 10 words are guaranteed to be in the database and are saved to your session.
                    </p>
                  </div>
                </div>

                <button className="secondary" onClick={handleLoadInitial}>
                  Load starter set
                </button>

                {wordPool.length > 0 && (
                  <div className="word-preview">
                    <p className="subtitle">Words to practice (ordered by difficulty)</p>
                    <ul>
                      {wordPool.slice(0, 6).map((word) => (
                        <li key={word.id}>
                          <span>{word.polish}</span>
                          <span>{word[languageSet]}</span>
                          <span className="error-rate">
                            {word.total_attempts > 0 
                              ? `${word.error_rate}% errors (${word.total_attempts} tries)`
                              : "New"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}

            {addMode === "verbs" && (
              <>
                <div className="instruction-card">
                  <p className="step">1</p>
                  <div>
                    <p className="instruction-title">Add verbs for conjugation practice</p>
                    <p className="instruction-body">
                      Enter a verb in {languageSet === "english" ? "English" : "Ukrainian"} (e.g., "to do", "to eat"). 
                      The system will generate all Polish conjugations automatically.
                    </p>
                  </div>
                </div>

                <div className="manual-entry">
                  <input
                    value={verbEntry}
                    onChange={(event) => setVerbEntry(event.target.value)}
                    type="text"
                    placeholder={`Type a verb in ${languageSet === "english" ? "English" : "Ukrainian"} (e.g., to do, to eat)`}
                    disabled={verbLoading}
                  />
                  <button onClick={handleVerbSubmit} disabled={verbLoading}>
                    {verbLoading ? "Generating..." : "Add verb"}
                  </button>
                </div>
                {verbStatus && <p className={`status ${verbStatus.type}`}>{verbStatus.message}</p>}

                {verbPool.length > 0 && (
                  <div className="word-preview">
                    <p className="subtitle">Verbs to practice (ordered by difficulty)</p>
                    <ul>
                      {verbPool.slice(0, 6).map((verb) => (
                        <li key={verb.id}>
                          <span>{verb.infinitive}</span>
                          <span>{verb[languageSet]}</span>
                          <span className="error-rate">
                            {verb.total_attempts > 0 
                              ? `${verb.error_rate}% errors (${verb.total_attempts} tries)`
                              : "New"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {activePage === "translation" && renderPracticePage("Translation")}
        {activePage === "writing" && renderPracticePage("Writing")}
        
        {activePage === "pronunciation" && (
          <section className="panel practice-panel">
            <div className="panel-header">
              <div>
                <p className="subtitle">Practice</p>
                <h2>Pronunciation mode</h2>
              </div>
              <button className="secondary" onClick={() => setActivePage("home")}>
                Back to main
              </button>
            </div>

            {!shuffledWords.length && (
              <p className="status info">
                Add words to your session first, then return here to practice.
              </p>
            )}

            <div className="practice-status">
              <p className={`status ${pronunciationStatus?.type ?? "info"}`}>
                {pronunciationStatus?.message ?? "Click Record and say the Polish word shown below."}
              </p>
            </div>

            <div className="practice-card pronunciation-card">
              <div className="practice-mirror">
                <p className="subtitle">Say this word in Polish:</p>
                <p className="prompt pronunciation-prompt">
                  {currentPronunciationWord?.polish ?? "Add words to start practicing."}
                </p>
                {currentPronunciationWord && (
                  <p className="translation-hint">
                    ({currentPronunciationWord[languageSet]})
                  </p>
                )}
              </div>
              
              <div className="pronunciation-controls">
                {!isRecording ? (
                  <button 
                    onClick={startRecording} 
                    disabled={!currentPronunciationWord}
                    className="record-btn"
                  >
                    🎤 Record
                  </button>
                ) : (
                  <button 
                    onClick={stopRecording}
                    className="record-btn recording"
                  >
                    ⏹ Stop Recording
                  </button>
                )}
                <button 
                  onClick={handlePronunciationSkip} 
                  disabled={!currentPronunciationWord || isRecording}
                  className="skip-btn"
                >
                  Skip
                </button>
                <button 
                  onClick={nextPronunciationWord} 
                  disabled={!currentPronunciationWord || isRecording}
                  className="secondary"
                >
                  Next word →
                </button>
              </div>
            </div>
          </section>
        )}

        {activePage === "endings" && (
          <section className="panel practice-panel">
            <div className="panel-header">
              <div>
                <p className="subtitle">Practice</p>
                <h2>Endings mode</h2>
              </div>
              <button className="secondary" onClick={() => setActivePage("home")}>
                Back to main
              </button>
            </div>

            {!verbPool.length && (
              <p className="status info">
                Add verbs to your session first. Go to "Add words" and select the "Verbs" tab.
              </p>
            )}

            {endingsStats && (
              <div className="endings-stats">
                <span>Today: {endingsStats.today_percentage}%</span>
                <span>Overall: {endingsStats.overall_percentage}%</span>
                <span>Verbs: {verbPool.length}</span>
              </div>
            )}

            <div className="practice-status">
              <p className={`status ${endingsStatus?.type ?? "info"}`}>
                {endingsStatus?.message ?? "Select the correct conjugation for the pronoun shown."}
              </p>
            </div>

            {endingsQuestion && (
              <div className="practice-card endings-card">
                <div className="practice-mirror">
                  <p className="subtitle">
                    {endingsQuestion.infinitive} ({endingsQuestion[languageSet]})
                  </p>
                  <p className="prompt endings-prompt">
                    <span className="pronoun">{endingsQuestion.pronoun}</span> ___
                  </p>
                </div>
                
                <div className="endings-options">
                  {endingsQuestion.options.map((option, index) => (
                    <button
                      key={index}
                      className="endings-option"
                      onClick={() => handleEndingsAnswer(option)}
                    >
                      {option}
                    </button>
                  ))}
                </div>

                <button 
                  className="skip-btn endings-skip"
                  onClick={handleEndingsSkip}
                >
                  Skip (I don't know)
                </button>
              </div>
            )}

            {!endingsQuestion && verbPool.length > 0 && (
              <div className="practice-card">
                <p>Loading question...</p>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
