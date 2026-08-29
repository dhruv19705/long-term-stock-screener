import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchQuestionnaire,
  previewQuestionnaire,
  submitQuestionnaire,
  type QuestionnairePreview,
  type RiskProfile,
} from "../api/client";

const PROFILE_KEY = "screener_risk_profile";

export function saveProfile(p: RiskProfile) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
}

export function loadProfile(): RiskProfile | null {
  const raw = localStorage.getItem(PROFILE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as RiskProfile;
  } catch {
    return null;
  }
}

const PROFILE_LABELS: Record<string, string> = {
  conservative: "Capital Preservation",
  moderate: "Balanced Growth",
  growth: "Growth Oriented",
  aggressive: "High Conviction",
};

function ProfilePreview({ preview }: { preview: QuestionnairePreview | undefined }) {
  if (!preview) return null;
  const scores = preview.profile_scores;
  const maxScore = Math.max(...Object.values(scores), 1);

  return (
    <div className="rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Profile preview</p>
      <p className="mt-1 font-display text-lg font-semibold text-ink">{preview.leading_profile_label}</p>
      <div className="mt-4 space-y-2">
        {Object.entries(PROFILE_LABELS).map(([id, label]) => {
          const val = scores[id] ?? 0;
          const pct = maxScore > 0 ? (val / maxScore) * 100 : 0;
          const active = id === preview.leading_profile_id;
          return (
            <div key={id}>
              <div className="mb-0.5 flex justify-between text-xs">
                <span className={active ? "font-semibold text-accent" : "text-slate-600"}>{label}</span>
                <span className="tabular-nums text-slate-400">{val}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full transition-all ${active ? "bg-accent" : "bg-slate-300"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {preview.profile_summary.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          {preview.profile_summary.slice(1, 4).map((line) => (
            <li key={line}>• {line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Questionnaire() {
  const { data, isLoading, error } = useQuery({ queryKey: ["questionnaire"], queryFn: fetchQuestionnaire });
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [reviewing, setReviewing] = useState(false);
  const [preview, setPreview] = useState<QuestionnairePreview | undefined>();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: submitQuestionnaire,
    onSuccess: (profile) => {
      saveProfile(profile);
      navigate("/recommendations");
    },
  });

  const questions = data?.questions ?? [];
  const chapters = data?.chapters ?? [];
  const q = questions[step];
  const currentChapter = q?.chapter ?? "goals";
  const chapterQuestions = useMemo(
    () => questions.filter((item) => item.chapter === currentChapter),
    [questions, currentChapter]
  );
  const chapterStep = chapterQuestions.findIndex((item) => item.id === q?.id) + 1;
  const progress = questions.length ? ((step + 1) / questions.length) * 100 : 0;

  useEffect(() => {
    if (Object.keys(answers).length === 0) return;
    previewQuestionnaire(answers)
      .then(setPreview)
      .catch(() => undefined);
  }, [answers]);

  if (isLoading) return <p className="text-slate-600">Loading questionnaire…</p>;
  if (error || !data || !q) return <p className="text-danger">Failed to load questionnaire. Is the API running?</p>;

  function select(optionId: string) {
    const next = { ...answers, [q.id]: optionId };
    setAnswers(next);
    if (step < questions.length - 1) {
      setStep(step + 1);
    } else {
      setReviewing(true);
    }
  }

  if (reviewing) {
    return (
      <section className="mx-auto max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Review</p>
        <h1 className="mt-1 font-display text-3xl font-bold text-ink">Your investor profile</h1>
        <p className="mt-2 text-slate-600">Confirm how we&apos;ll match stocks to your preferences.</p>

        <div className="mt-8 rounded-2xl bg-white/95 p-6 shadow-sm ring-1 ring-slate-200/60">
          <h2 className="font-display text-2xl font-semibold">{preview?.leading_profile_label ?? "Your profile"}</h2>
          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            {(preview?.profile_summary ?? []).map((line) => (
              <li key={line} className="flex gap-2">
                <span className="text-accent">•</span>
                {line}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => mutation.mutate(answers)}
            disabled={mutation.isPending}
            className="rounded-xl bg-accent px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-accent/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Matching stocks…" : "See my picks"}
          </button>
          <button
            type="button"
            onClick={() => {
              setReviewing(false);
              setStep(questions.length - 1);
            }}
            className="rounded-xl bg-white/90 px-4 py-2.5 text-sm font-medium ring-1 ring-slate-200/80 hover:ring-accent/40"
          >
            Edit answers
          </button>
        </div>
      </section>
    );
  }

  const activeChapterMeta = chapters.find((c) => c.id === currentChapter);

  return (
    <section className="grid gap-8 lg:grid-cols-[1fr_280px]">
      <div className="mx-auto w-full max-w-2xl lg:mx-0">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Investor profile</p>
        <h1 className="mt-1 font-display text-4xl font-bold text-ink">How do you invest?</h1>
        <p className="mt-2 text-slate-600">
          We use your answers to filter the universe and rank stocks that fit your risk tolerance.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {chapters.map((ch) => {
            const chQs = questions.filter((item) => item.chapter === ch.id);
            const answered = chQs.filter((item) => answers[item.id]).length;
            const done = answered === chQs.length;
            const active = ch.id === currentChapter;
            return (
              <span
                key={ch.id}
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  active
                    ? "bg-accent text-white"
                    : done
                      ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/70"
                      : "bg-white/90 text-slate-500 ring-1 ring-slate-200/70"
                }`}
              >
                {ch.label}
              </span>
            );
          })}
        </div>

        <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-slate-200">
          <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {activeChapterMeta?.label} · Question {chapterStep} of {chapterQuestions.length}
        </p>

        <div className="mt-6 rounded-2xl bg-white/95 p-6 shadow-sm ring-1 ring-slate-200/60">
          <p className="text-sm text-slate-500">{activeChapterMeta?.description}</p>
          <h2 className="mt-2 font-display text-2xl font-semibold">{q.text}</h2>
          <div className="mt-6 flex flex-col gap-3">
            {q.options.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => select(o.id)}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition hover:border-accent hover:bg-accent/5 ${
                  answers[q.id] === o.id ? "border-accent bg-accent/10" : "border-slate-200 bg-white"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
          {step > 0 && (
            <button
              type="button"
              className="mt-6 text-sm text-slate-500 hover:text-ink"
              onClick={() => setStep(step - 1)}
            >
              ← Back
            </button>
          )}
        </div>

        <p className="mt-4 text-center text-sm text-slate-500">
          Already have a profile?{" "}
          <Link to="/recommendations" className="text-accent hover:underline">
            View recommendations
          </Link>
        </p>
      </div>

      <aside className="hidden lg:block">
        <ProfilePreview preview={preview} />
      </aside>
    </section>
  );
}
