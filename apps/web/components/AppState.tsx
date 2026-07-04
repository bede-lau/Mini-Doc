"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type {
  Answer,
  BenchmarkRunInfo,
  BenchmarkSummary,
  DocumentMeta,
  ReportResponse,
} from "@/lib/types";

type ReportType =
  | "kyc_beneficial_ownership"
  | "technology_risk_compliance"
  | "insurance_claims_review"
  | "general_compliance_intelligence";

interface QaState {
  question: string;
  answer: Answer | null;
  loading: boolean;
  error: string | null;
  showChunks: boolean;
  setQuestion: (question: string) => void;
  setShowChunks: (show: boolean | ((current: boolean) => boolean)) => void;
  selectQuestion: (question: string) => void;
  ask: (question?: string) => Promise<void>;
}

interface ReportState {
  type: ReportType;
  report: ReportResponse | null;
  loading: boolean;
  error: string | null;
  setType: (type: ReportType) => void;
  generate: () => Promise<void>;
}

interface BenchmarkState {
  runId: string;
  latest: BenchmarkSummary | null;
  runs: BenchmarkRunInfo[];
  loading: boolean;
  loadingRuns: boolean;
  deletingRun: string | null;
  error: string | null;
  setRunId: (runId: string) => void;
  loadRuns: () => Promise<void>;
  run: () => Promise<void>;
  selectRun: (runId: string) => Promise<void>;
  deleteRun: (runId: string) => Promise<void>;
}

interface LibraryState {
  docs: DocumentMeta[];
  loading: boolean;
  error: string | null;
  busy: string | null;
  load: () => Promise<void>;
  upload: (file: File) => Promise<void>;
  deleteDocument: (documentId: string) => Promise<void>;
  parse: () => Promise<void>;
  index: () => Promise<void>;
}

interface AppState {
  library: LibraryState;
  qa: QaState;
  reports: ReportState;
  benchmark: BenchmarkState;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [libraryBusy, setLibraryBusy] = useState<string | null>(null);

  const [qaQuestion, setQaQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState<Answer | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [showChunks, setShowChunks] = useState(false);

  const [reportType, setReportType] = useState<ReportType>("kyc_beneficial_ownership");
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const [runId, setRunId] = useState("run_001");
  const [latest, setLatest] = useState<BenchmarkSummary | null>(null);
  const [runs, setRuns] = useState<BenchmarkRunInfo[]>([]);
  const [benchmarkLoading, setBenchmarkLoading] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [deletingRun, setDeletingRun] = useState<string | null>(null);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLibraryLoading(true);
    setLibraryError(null);
    try {
      const r = await api.documents();
      setDocs(r.documents);
    } catch (e) {
      setLibraryError(String(e));
    } finally {
      setLibraryLoading(false);
    }
  }, []);

  const uploadDocument = useCallback(
    async (file: File) => {
      setLibraryBusy("upload");
      setLibraryError(null);
      try {
        await api.ingest(file);
        await loadDocuments();
      } catch (e) {
        setLibraryError(String(e));
      } finally {
        setLibraryBusy(null);
      }
    },
    [loadDocuments],
  );

  const deleteDocument = useCallback(
    async (documentId: string) => {
      setLibraryBusy(`delete:${documentId}`);
      setLibraryError(null);
      try {
        const result = await api.deleteDocument(documentId);
        setDocs((current) => current.filter((doc) => doc.document_id !== documentId));
        if (result.errors.length) {
          setLibraryError(result.errors.join("; "));
        }
      } catch (e) {
        setLibraryError(String(e));
      } finally {
        setLibraryBusy(null);
      }
    },
    [],
  );

  const parseDocuments = useCallback(
    async () => {
      setLibraryBusy("parse:hybrid");
      setLibraryError(null);
      try {
        await api.parse("hybrid");
        await loadDocuments();
      } catch (e) {
        setLibraryError(String(e));
      } finally {
        setLibraryBusy(null);
      }
    },
    [loadDocuments],
  );

  const indexDocuments = useCallback(async () => {
    setLibraryBusy("index");
    setLibraryError(null);
    try {
      await api.index("hybrid");
    } catch (e) {
      setLibraryError(String(e));
    } finally {
      setLibraryBusy(null);
    }
  }, []);

  const ask = useCallback(
    async (q?: string) => {
      const query = (q ?? qaQuestion).trim();
      if (!query) return;
      setQaQuestion(query);
      setQaLoading(true);
      setQaError(null);
      setQaAnswer(null);
      try {
        setQaAnswer(await api.ask(query));
      } catch (e) {
        setQaError(String(e));
      } finally {
        setQaLoading(false);
      }
    },
    [qaQuestion],
  );

  const selectQuestion = useCallback((q: string) => {
    setQaQuestion(q.trim());
    setQaAnswer(null);
    setQaError(null);
    setShowChunks(false);
  }, []);

  const generate = useCallback(async () => {
    setReportLoading(true);
    setReportError(null);
    setReport(null);
    try {
      setReport(await api.generateReport(reportType));
    } catch (e) {
      setReportError(String(e));
    } finally {
      setReportLoading(false);
    }
  }, [reportType]);

  const loadRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      setRuns((await api.benchmarkResults()).runs);
    } catch {
      /* runs list is optional while backend is unavailable */
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  const selectRun = useCallback(async (selectedRunId: string) => {
    const clean = selectedRunId.trim();
    if (!clean) return;
    setRunId(clean);
    setBenchmarkLoading(true);
    setBenchmarkError(null);
    try {
      setLatest(await api.benchmarkResult(clean));
    } catch (e) {
      setBenchmarkError(String(e));
    } finally {
      setBenchmarkLoading(false);
    }
  }, []);

  const run = useCallback(async () => {
    setBenchmarkLoading(true);
    setBenchmarkError(null);
    try {
      const res = await api.runBenchmark(runId);
      setLatest(res);
      await loadRuns();
    } catch (e) {
      setBenchmarkError(String(e));
    } finally {
      setBenchmarkLoading(false);
    }
  }, [loadRuns, runId]);

  const deleteRun = useCallback(
    async (targetRunId: string) => {
      const clean = targetRunId.trim();
      if (!clean) return;
      setDeletingRun(clean);
      setBenchmarkError(null);
      try {
        await api.deleteBenchmarkRun(clean);
        setRuns((current) => current.filter((r) => r.run_id !== clean));
        if (latest?.run_id === clean) setLatest(null);
        if (runId === clean) setRunId("run_001");
      } catch (e) {
        setBenchmarkError(String(e));
        await loadRuns();
      } finally {
        setDeletingRun(null);
      }
    },
    [latest, loadRuns, runId],
  );

  useEffect(() => {
    loadDocuments();
    loadRuns();
  }, [loadDocuments, loadRuns]);

  const value = useMemo<AppState>(
    () => ({
      library: {
        docs,
        loading: libraryLoading,
        error: libraryError,
        busy: libraryBusy,
        load: loadDocuments,
        upload: uploadDocument,
        deleteDocument,
        parse: parseDocuments,
        index: indexDocuments,
      },
      qa: {
        question: qaQuestion,
        answer: qaAnswer,
        loading: qaLoading,
        error: qaError,
        showChunks,
        setQuestion: setQaQuestion,
        setShowChunks,
        selectQuestion,
        ask,
      },
      reports: {
        type: reportType,
        report,
        loading: reportLoading,
        error: reportError,
        setType: setReportType,
        generate,
      },
      benchmark: {
        runId,
        latest,
        runs,
        loading: benchmarkLoading,
        loadingRuns,
        deletingRun,
        error: benchmarkError,
        setRunId,
        loadRuns,
        run,
        selectRun,
        deleteRun,
      },
    }),
    [
      ask,
      benchmarkError,
      benchmarkLoading,
      deleteRun,
      deletingRun,
      docs,
      deleteDocument,
      generate,
      indexDocuments,
      latest,
      libraryBusy,
      libraryError,
      libraryLoading,
      loadDocuments,
      loadRuns,
      loadingRuns,
      parseDocuments,
      qaAnswer,
      qaError,
      qaLoading,
      qaQuestion,
      report,
      reportError,
      reportLoading,
      reportType,
      run,
      runId,
      runs,
      selectQuestion,
      selectRun,
      showChunks,
      uploadDocument,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return ctx;
}
