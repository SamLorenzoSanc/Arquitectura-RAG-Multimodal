"use client";

import { useEffect, useMemo, useState } from "react";
import api from "@/api";

type TestItem = {
  id: number;
  question: string;
  keywords: string[];
  reference_answer: string;
  category: string;
};

type RetrievalResult = {
  test_id: number;
  question: string;
  category: string;
  retrieval: {
    mrr: number;
    ndcg: number;
    keywords_found: number;
    total_keywords: number;
    keyword_coverage: number;
  };
};

type AnswerResult = {
  test_id: number;
  question: string;
  category: string;
  generated_answer: string;
  evaluation: {
    feedback: string;
    accuracy: number;
    precision: number;
    completeness: number;
    relevance: number;
  };
};

export default function AuditPage() {
  const [tests, setTests] = useState<TestItem[]>([]);
  const [retrieval, setRetrieval] = useState<RetrievalResult[]>([]);
  const [answers, setAnswers] = useState<AnswerResult[]>([]);
  const [loadingTests, setLoadingTests] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadTests();
  }, []);

  const loadTests = async () => {
    setLoadingTests(true);
    setError(null);
    try {
      const { data } = await api.get("/chat/evaluation/tests");
      setTests(data.tests ?? []);
    } catch (err) {
      setError("No se pudieron cargar los tests.");
    } finally {
      setLoadingTests(false);
    }
  };

  const runRetrieval = async () => {
    setRunning(true);
    setError(null);
    try {
      const results: RetrievalResult[] = [];
      for (const test of tests) {
        const { data } = await api.post(`/chat/evaluation/retrieval/${test.id}`);
        results.push(data);
      }
      setRetrieval(results);
    } catch {
      setError("Error ejecutando evaluación de retrieval.");
    } finally {
      setRunning(false);
    }
  };

  const runAnswers = async () => {
    setRunning(true);
    setError(null);
    try {
      const results: AnswerResult[] = [];
      for (const test of tests) {
        const { data } = await api.post(`/chat/evaluation/answer/${test.id}`);
        results.push(data);
      }
      setAnswers(results);
    } catch {
      setError("Error ejecutando evaluación de respuestas.");
    } finally {
      setRunning(false);
    }
  };

  const runAll = async () => {
    if (!tests.length) return;
    setRunning(true);
    setError(null);
    try {
      const retrievalResults: RetrievalResult[] = [];
      const answerResults: AnswerResult[] = [];

      for (const test of tests) {
        const r = await api.post(`/chat/evaluation/retrieval/${test.id}`);
        retrievalResults.push(r.data);

        const a = await api.post(`/chat/evaluation/answer/${test.id}`);
        answerResults.push(a.data);
      }

      setRetrieval(retrievalResults);
      setAnswers(answerResults);
    } catch {
      setError("Error ejecutando la auditoría completa.");
    } finally {
      setRunning(false);
    }
  };

  const averages = useMemo(() => {
    const avg = (arr: number[]) =>
      arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    return {
      mrr: avg(retrieval.map((r) => Number(r.retrieval.mrr) || 0)),
      ndcg: avg(retrieval.map((r) => Number(r.retrieval.ndcg) || 0)),
      accuracy: avg(answers.map((a) => Number(a.evaluation.accuracy) || 0)),
      precision: avg(answers.map((a) => Number(a.evaluation.precision) || 0)),
      completeness: avg(answers.map((a) => Number(a.evaluation.completeness) || 0)),
      relevance: avg(answers.map((a) => Number(a.evaluation.relevance) || 0)),
    };
  }, [retrieval, answers]);

  if (loadingTests) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="animate-pulse text-emerald-600">Cargando auditoría...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-emerald-600">
              Auditoría RAG
            </p>
            <h1 className="text-3xl font-extrabold text-slate-900">
              Evaluación del modelo
            </h1>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void loadTests()}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Recargar tests
            </button>
            <button
              onClick={() => void runRetrieval()}
              disabled={!tests.length || running}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              Retrieval
            </button>
            <button
              onClick={() => void runAnswers()}
              disabled={!tests.length || running}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              Respuestas
            </button>
            <button
              onClick={() => void runAll()}
              disabled={!tests.length || running}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
            >
              Ejecutar todo
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          <MetricCard label="MRR" value={averages.mrr} />
          <MetricCard label="nDCG" value={averages.ndcg} />
          <MetricCard label="Accuracy" value={averages.accuracy} />
          <MetricCard label="Precision" value={averages.precision} />
          <MetricCard label="Completeness" value={averages.completeness} />
          <MetricCard label="Relevance" value={averages.relevance} />
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <Panel title="Resultados retrieval">
            {retrieval.length === 0 ? (
              <EmptyState text="No hay resultados de retrieval todavía." />
            ) : (
              <div className="space-y-3">
                {retrieval.map((item) => (
                  <div key={item.test_id} className="rounded-xl bg-slate-50 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="font-semibold text-slate-800">{item.category}</p>
                      <span className="text-xs text-slate-500">Test {item.test_id}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <MiniStat label="MRR" value={item.retrieval.mrr.toFixed(3)} />
                      <MiniStat label="nDCG" value={item.retrieval.ndcg.toFixed(3)} />
                      <MiniStat
                        label="Coverage"
                        value={`${item.retrieval.keyword_coverage.toFixed(1)}%`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Resultados calidad">
            {answers.length === 0 ? (
              <EmptyState text="No hay resultados de respuesta todavía." />
            ) : (
              <div className="space-y-3">
                {answers.map((item) => (
                  <div key={item.test_id} className="rounded-xl bg-slate-50 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="font-semibold text-slate-800">{item.category}</p>
                      <span className="text-xs text-slate-500">Test {item.test_id}</span>
                    </div>
                    <div className="grid grid-cols-4 gap-3 text-sm">
                      <MiniStat label="Accuracy" value={item.evaluation.accuracy.toFixed(2)} />
                      <MiniStat label="Precision" value={item.evaluation.precision.toFixed(2)} />
                      <MiniStat label="Completeness" value={item.evaluation.completeness.toFixed(2)} />
                      <MiniStat label="Relevance" value={item.evaluation.relevance.toFixed(2)} />
                    </div>
                    <p className="mt-3 text-xs text-slate-500">{item.evaluation.feedback}</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-extrabold text-slate-900">{value.toFixed(3)}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
      {children}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-400">{text}</div>;
}