import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
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

  useEffect(() => {
    fetchStats();
    fetchSession();
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
  }, [activePage, languageSet]);

  const practiceDirection =
    activePage === "translation" ? "translation" : activePage === "writing" ? "writing" : null;
  const currentWord =
    practiceDirection && wordPool.length ? wordPool[practiceIndex % wordPool.length] : null;
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

    try {
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

  const handlePracticeSubmit = async (event) => {
    event?.preventDefault?.();
    if (!currentWord || !practiceDirection) {
      return;
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

      {!wordPool.length && (
        <p className="status info">
          Add words to your session first, then return here to practice.
        </p>
      )}

      <div className="practice-status">
        <p className={`status ${practiceStatus?.type ?? "info"}`}>
          {practiceStatus?.message ?? "Practice results appear here after each submission."}
        </p>
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
        <button type="submit" disabled={!practiceDirection || !currentWord}>
          Submit answer
        </button>
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

            <div className="instruction-card">
              <p className="step">1</p>
              <div>
                <p className="instruction-title">Validate new words</p>
                <p className="instruction-body">
                  The database checks every manually entered word and can expand the dictionary with GPT.
                </p>
              </div>
            </div>

            <div className="manual-entry">
              <input
                value={manualEntry}
                onChange={(event) => setManualEntry(event.target.value)}
                type="text"
                placeholder="Type Polish, English or Ukrainian word"
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
                <p className="subtitle">Recent entries</p>
                <ul>
                  {wordPool.slice(-4).map((word) => (
                    <li key={word.id}>
                      <span>{word.polish}</span>
                      <span>{word[languageSet]}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {activePage === "translation" && renderPracticePage("Translation")}
        {activePage === "writing" && renderPracticePage("Writing")}
      </main>
    </div>
  );
}

export default App;
