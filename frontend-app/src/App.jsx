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
};

const normalize = (value = "") =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

const buildUrl = (path) => `${API_BASE_URL}/${path}`;

function App() {
  const [languageSet, setLanguageSet] = useState("english");
  const [manualEntry, setManualEntry] = useState("");
  const [manualStatus, setManualStatus] = useState(null);
  const [wordPool, setWordPool] = useState([]);
  const [practiceDirection, setPracticeDirection] = useState(null);
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [practiceStatus, setPracticeStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (!wordPool.length) {
      setPracticeDirection(null);
      setPracticeIndex(0);
    }
  }, [wordPool]);

  const currentWord =
    practiceDirection && wordPool.length ? wordPool[practiceIndex % wordPool.length] : null;
  const targetLabel = LANGUAGE_LABELS[languageSet];
  const prompt =
    practiceDirection === "translation" ? currentWord?.polish : currentWord?.[languageSet];
  const expectedResponse =
    practiceDirection === "translation" ? currentWord?.[languageSet] : currentWord?.polish;

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

  const handleLoadInitial = async () => {
    try {
      const response = await fetch(buildUrl("words/initial?count=10"));
      if (!response.ok) {
        throw new Error("Unable to load starter set");
      }
      const payload = await response.json();
      setWordPool(payload);
      setManualStatus({ type: "success", message: "Loaded the first 10 words as your starter set." });
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

      setWordPool((previous) => {
        if (previous.some((entry) => entry.id === payload.word.id)) {
          setManualStatus({
            type: "info",
            message: `${payload.word.polish} is already in your practice list.`,
          });
          return previous;
        }
        setManualStatus({
          type: "success",
          message: `Saved ${payload.word.polish} (${FIELD_LABELS[payload.matched_field] ?? "entry"}) for practice.`,
        });
        return [...previous, payload.word];
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

  const handleStartPractice = (direction) => {
    if (!wordPool.length) {
      setPracticeStatus({ type: "info", message: "Add some words before you start practicing." });
      return;
    }
    setPracticeDirection(direction);
    setPracticeIndex(0);
    setAnswer("");
    setPracticeStatus({
      type: "info",
      message:
        direction === "translation"
          ? "Translate the Polish prompt into the target language."
          : "Write the Polish word that matches the translation.",
    });
  };

  const handlePracticeSubmit = async (event) => {
    event?.preventDefault?.();
    if (!currentWord) {
      return;
    }

    if (!answer.trim()) {
      setPracticeStatus({ type: "error", message: "Try answering before submitting." });
      return;
    }

    const normalizedAnswer = normalize(answer);
    const normalizedExpected = normalize(expectedResponse ?? "");
    const isCorrect = normalizedAnswer === normalizedExpected;
    const baseMessage = isCorrect
      ? "Correct! Keep going."
      : `The correct answer is “${expectedResponse}”.`;
    setPracticeStatus({ type: isCorrect ? "success" : "error", message: baseMessage });

    try {
      const response = await fetch(buildUrl("practice/submit"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word_id: currentWord.id,
          language_set: languageSet,
          direction: practiceDirection,
          was_correct: isCorrect,
        }),
      });

      if (!response.ok) {
        throw new Error("Practice sync failed");
      }

      setStats(await response.json());
    } catch (error) {
      console.error(error);
      setPracticeStatus((previous) => ({
        type: previous?.type ?? "error",
        message: `${previous?.message ?? baseMessage} Progress could not be recorded.`,
      }));
    }
    setAnswer("");
    setPracticeIndex((previous) => (previous + 1) % wordPool.length);
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Polingo</p>
          <h1>Polish practice that respects your tempo</h1>
          <p className="lede">
            Start with the built-in list or validate the words you’ve been studying manually. Once the
            deck feels right, decide whether you want to translate or write in Polish and track your
            cumulative progress in the corner.
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
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="subtitle">Language set</p>
              <select
                value={languageSet}
                onChange={(event) => setLanguageSet(event.target.value)}
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

          <div className="instruction-card">
            <p className="step">1</p>
            <div>
              <p className="instruction-title">Validate new words</p>
              <p className="instruction-body">
                The database checks every manually entered word so you catch spelling mistakes before
                you start practicing.
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
                These first 10 words are guaranteed to be in the database and let you jump straight
                into practice.
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

          <ol className="flow">
            <li>Validate words or load a proven starter collection.</li>
            <li>Choose translation or writing mode depending on how you want to train.</li>
            <li>Submit answers and watch your daily percentage update instantly.</li>
          </ol>
        </section>

        <section className="panel practice-panel">
          <div className="practice-header">
            <div>
              <p className="subtitle">Practice</p>
              <h2>{practiceDirection ? `${practiceDirection} mode` : "Choose a practice mode"}</h2>
            </div>
            <div className="mode-buttons">
              <button onClick={() => handleStartPractice("translation")}>Translation practice</button>
              <button onClick={() => handleStartPractice("writing")}>Writing practice</button>
            </div>
          </div>

          <div className="practice-status">
            <p className={`status ${practiceStatus?.type ?? "info"}`}>
              {practiceStatus?.message ?? "Practice results appear here after each submission."}
            </p>
          </div>

          <form onSubmit={handlePracticeSubmit} className="practice-card">
            <div className="practice-mirror">
              <p className="subtitle">Target language: {targetLabel}</p>
              <p className="prompt">
                {prompt ?? "Add words and choose a mode before starting."}
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
      </main>
    </div>
  );
}

export default App;
