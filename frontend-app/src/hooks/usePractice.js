import { useState, useCallback, useRef, useEffect } from "react";

function shuffleArray(array) {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function usePractice({ wordPool, languageSet }) {
  const [practiceMode, setPracticeMode] = useState("translation"); // translation | writing | choose
  const [practiceDirection, setPracticeDirection] = useState("from_polish");
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [practiceStatus, setPracticeStatus] = useState(null);
  const [shuffledWords, setShuffledWords] = useState([]);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [chooseQuestion, setChooseQuestion] = useState(null);
  const practiceStatusTimeoutRef = useRef(null);

  // Initialize shuffledWords from wordPool
  useEffect(() => {
    setShuffledWords(shuffleArray(wordPool));
  }, [wordPool]);

  const resetPracticeState = useCallback(() => {
    setAnswer("");
    setPracticeStatus(null);
    setPracticeIndex(0);
    setLastAnswer(null);
    setChooseQuestion(null);
  }, []);

  const reshuffleWords = useCallback(() => {
    setShuffledWords(shuffleArray(wordPool));
  }, [wordPool]);

  return {
    practiceMode, setPracticeMode,
    practiceDirection, setPracticeDirection,
    practiceIndex, setPracticeIndex,
    answer, setAnswer,
    practiceStatus, setPracticeStatus,
    shuffledWords, setShuffledWords,
    lastAnswer, setLastAnswer,
    chooseQuestion, setChooseQuestion,
    practiceStatusTimeoutRef,
    resetPracticeState,
    reshuffleWords,
  };
}
