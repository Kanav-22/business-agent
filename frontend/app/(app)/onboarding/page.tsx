"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  CircleAlert,
  ClipboardList,
  FileUp,
  Loader2,
  RefreshCw,
  Save,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { API_BASE, getJson } from "@/lib/api";
import type {
  BusinessProfile,
  IntakeQuestion,
  IntakeQuestionsResponse,
  IntakeUpload,
  IntakeUploadResponse,
  ReportSummary,
} from "@/lib/types";

const POLL_MS = 3000;
const MAX_POLL_ATTEMPTS = 40;
const BUTTON_FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950";
const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-base text-slate-100 outline-none transition-colors motion-reduce:transition-none placeholder:text-slate-600 focus:border-violet-500 focus-visible:ring-2 focus-visible:ring-violet-400/70 disabled:cursor-not-allowed disabled:opacity-50";

type SaveState = {
  phase: "idle" | "saving" | "saved" | "error";
  message?: string;
};

type UploadState = {
  phase: "uploading" | "success" | "error";
  filename: string;
  message: string;
};

type ReviewState = {
  phase: "idle" | "starting" | "polling" | "success" | "error";
  message?: string;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function apiError(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // A status-bearing fallback is more useful than a second parsing failure.
  }
  return `${fallback} (HTTP ${response.status})`;
}

function isFilled(value: string | undefined): boolean {
  return Boolean(value?.trim());
}

function QuestionField({
  question,
  value,
  disabled,
  onChange,
}: {
  question: IntakeQuestion;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const id = `business-${question.key}`;
  const helperId = `${id}-why`;
  const maxLength = question.type === "long" ? 4000 : 1500;
  const shared = {
    id,
    value,
    disabled,
    required: question.required,
    "aria-describedby": helperId,
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
    ) => onChange(event.target.value),
  };

  return (
    <div className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/60 p-4 sm:p-5">
      <label htmlFor={id} className="block text-sm font-medium leading-relaxed text-slate-100">
        {question.question}
        {question.required && (
          <>
            <span className="ml-1 text-amber-300" aria-hidden="true">
              *
            </span>
            <span className="sr-only"> Required</span>
          </>
        )}
      </label>
      <p id={helperId} className="mt-1 text-xs leading-relaxed text-slate-500">
        {question.why}
      </p>

      <div className="mt-3">
        {question.type === "long" ? (
          <textarea {...shared} rows={7} maxLength={maxLength} className={FIELD_CLASS} />
        ) : question.type === "choice" ? (
          <select {...shared} className={FIELD_CLASS}>
            <option value="">Select an option</option>
            {(question.choices ?? []).map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        ) : (
          <input
            {...shared}
            type={question.type === "number" ? "number" : "text"}
            maxLength={question.type === "number" ? undefined : maxLength}
            className={FIELD_CLASS}
          />
        )}
      </div>
      <div className="mt-1 text-right text-[11px] tabular-nums text-slate-600">
        {value.length}/{maxLength}
      </div>
    </div>
  );
}

function StatusNotice({ state }: { state: SaveState }) {
  if (state.phase === "idle") return null;
  const failed = state.phase === "error";
  return (
    <p
      className={clsx(
        "flex min-h-6 items-center gap-2 text-sm",
        failed ? "text-red-300" : "text-slate-400",
      )}
      role={failed ? "alert" : "status"}
      aria-live="polite"
    >
      {state.phase === "saving" ? (
        <Loader2 size={14} className="animate-spin motion-reduce:animate-none" />
      ) : failed ? (
        <CircleAlert size={14} />
      ) : (
        <CheckCircle2 size={14} className="text-emerald-400" />
      )}
      {state.message}
    </p>
  );
}

export default function OnboardingPage() {
  const [schema, setSchema] = useState<IntakeQuestionsResponse | null>(null);
  const [profile, setProfile] = useState<BusinessProfile>({});
  const [activeStep, setActiveStep] = useState(0);
  const [completedSections, setCompletedSections] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({ phase: "idle" });
  const [uploadStates, setUploadStates] = useState<Record<string, UploadState>>({});
  const [reviewState, setReviewState] = useState<ReviewState>({ phase: "idle" });
  const [reviewReport, setReviewReport] = useState<ReportSummary | null>(null);
  const stepHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const previousStepRef = useRef(activeStep);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [nextSchema, storedProfile] = await Promise.all([
        getJson<IntakeQuestionsResponse>("/api/intake/questions"),
        getJson<BusinessProfile>("/api/business"),
      ]);
      const normalized = Object.fromEntries(
        nextSchema.questions.map((question) => [
          question.key,
          storedProfile[question.key] ?? "",
        ]),
      );
      const prefilled = new Set<string>();
      for (const section of nextSchema.sections) {
        const questions = nextSchema.questions.filter((question) => question.section === section);
        const requiredReady = questions.every(
          (question) => !question.required || isFilled(normalized[question.key]),
        );
        if (requiredReady && questions.some((question) => isFilled(normalized[question.key]))) {
          prefilled.add(section);
        }
      }
      setSchema(nextSchema);
      setProfile(normalized);
      setCompletedSections(prefilled);
      setActiveStep(0);
    } catch (error) {
      setLoadError(String(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (previousStepRef.current !== activeStep) {
      stepHeadingRef.current?.focus();
      previousStepRef.current = activeStep;
    }
  }, [activeStep]);

  const sections = schema?.sections ?? [];
  const sectionCount = sections.length;
  const uploadStep = sectionCount;
  const finishStep = sectionCount + 1;
  const stepLabels = useMemo(() => [...sections, "Uploads", "Finish"], [sections]);
  const activeSection = activeStep < sectionCount ? sections[activeStep] : null;
  const activeQuestions = useMemo(
    () =>
      activeSection
        ? (schema?.questions ?? []).filter((question) => question.section === activeSection)
        : [],
    [activeSection, schema],
  );
  const requiredQuestions = useMemo(
    () => (schema?.questions ?? []).filter((question) => question.required),
    [schema],
  );
  const requiredAnswered = requiredQuestions.filter((question) =>
    isFilled(profile[question.key]),
  ).length;
  const missingRequired = requiredQuestions.filter(
    (question) => !isFilled(profile[question.key]),
  );
  const requiredComplete = requiredAnswered === requiredQuestions.length;
  const completedSectionNames = new Set(
    sections.filter((section) => {
      if (!completedSections.has(section)) return false;
      return (schema?.questions ?? [])
        .filter((question) => question.section === section)
        .every((question) => !question.required || isFilled(profile[question.key]));
    }),
  );
  const completedCount = completedSectionNames.size;
  const progressPercent =
    requiredQuestions.length > 0
      ? Math.round((requiredAnswered / requiredQuestions.length) * 100)
      : 0;
  const saving = saveState.phase === "saving";
  const reviewRunning = reviewState.phase === "starting" || reviewState.phase === "polling";
  const uploadsInFlight = Object.values(uploadStates).some(
    (state) => state.phase === "uploading",
  );

  const updateAnswer = (question: IntakeQuestion, value: string) => {
    setProfile((current) => ({ ...current, [question.key]: value }));
    if (question.required && !value.trim()) {
      setCompletedSections((current) => {
        const next = new Set(current);
        next.delete(question.section);
        return next;
      });
    }
    if (saveState.phase !== "idle") setSaveState({ phase: "idle" });
  };

  const saveCurrentSection = async (): Promise<boolean> => {
    if (!activeSection) return true;
    const values = Object.fromEntries(
      activeQuestions
        .map((question) => [question.key, profile[question.key]?.trim() ?? ""])
        .filter(([, value]) => Boolean(value)),
    );
    setSaveState({ phase: "saving", message: `Saving ${activeSection}…` });
    try {
      if (Object.keys(values).length > 0) {
        const response = await fetch(`${API_BASE}/api/business`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ values }),
        });
        if (!response.ok) {
          throw new Error(await apiError(response, `Could not save ${activeSection}`));
        }
        const saved = (await response.json()) as BusinessProfile;
        setProfile((current) => ({ ...current, ...saved }));
      }
      setCompletedSections((current) => new Set(current).add(activeSection));
      setSaveState({ phase: "saved", message: `${activeSection} saved.` });
      return true;
    } catch (error) {
      setSaveState({ phase: "error", message: String(error) });
      return false;
    }
  };

  const goToStep = async (nextStep: number) => {
    if (nextStep === activeStep || saving || reviewRunning) return;
    if (nextStep === finishStep && uploadsInFlight) return;
    if (activeSection && !(await saveCurrentSection())) return;
    setActiveStep(Math.max(0, Math.min(nextStep, finishStep)));
  };

  const uploadFile = async (upload: IntakeUpload, file: File) => {
    setUploadStates((current) => ({
      ...current,
      [upload.key]: {
        phase: "uploading",
        filename: file.name,
        message: "Uploading and checking the file…",
      },
    }));
    const body = new FormData();
    body.append("kind", upload.key);
    body.append("file", file);
    try {
      const response = await fetch(`${API_BASE}/api/intake/upload`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        throw new Error(await apiError(response, `Could not store ${file.name}`));
      }
      const result = (await response.json()) as IntakeUploadResponse;
      setUploadStates((current) => ({
        ...current,
        [upload.key]: {
          phase: "success",
          filename: file.name,
          message: result.next ?? "Stored for the analyst review.",
        },
      }));
    } catch (error) {
      setUploadStates((current) => ({
        ...current,
        [upload.key]: {
          phase: "error",
          filename: file.name,
          message: String(error),
        },
      }));
    }
  };

  const runReview = async () => {
    if (!requiredComplete || reviewRunning || uploadsInFlight) return;
    setReviewReport(null);
    setReviewState({ phase: "starting", message: "Starting the analyst team…" });
    const startedAt = Date.now();
    try {
      const response = await fetch(`${API_BASE}/api/venture/intake_review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: profile.name?.trim() || "our business" }),
      });
      if (!response.ok) {
        throw new Error(await apiError(response, "Could not start the intake review"));
      }
      setReviewState({
        phase: "polling",
        message: "CFO, CMO, and Risk are studying the business…",
      });
      for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
        await sleep(POLL_MS);
        const reports = await getJson<ReportSummary[]>("/api/reports?kind=intake&limit=20");
        const review = reports.find(
          (report) =>
            report.title.startsWith("Business intake review:") &&
            new Date(report.created_at).getTime() > startedAt,
        );
        if (review) {
          setReviewReport(review);
          setReviewState({
            phase: "success",
            message: "The team has studied the business and saved its findings to memory.",
          });
          return;
        }
      }
      throw new Error("The review is still running after two minutes. Check Reports shortly.");
    } catch (error) {
      setReviewState({ phase: "error", message: String(error) });
    }
  };

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-5xl items-center justify-center p-4 sm:p-8">
        <div className="flex items-center gap-3 text-sm text-slate-400" role="status">
          <Loader2 size={18} className="animate-spin motion-reduce:animate-none" />
          Loading the business interview…
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-8">
        <div className="rounded-xl border border-red-900/70 bg-red-950/30 p-6" role="alert">
          <div className="flex items-center gap-2 text-sm font-medium text-red-200">
            <CircleAlert size={18} /> Business setup could not load
          </div>
          <p className="mt-2 break-words text-sm text-red-300/80">{loadError}</p>
          <button
            type="button"
            onClick={() => void load()}
            className={clsx(
              BUTTON_FOCUS,
              "mt-5 flex min-h-11 items-center gap-2 rounded-lg border border-red-800 px-4 text-sm text-red-100 hover:bg-red-950",
            )}
          >
            <RefreshCw size={15} /> Try again
          </button>
        </div>
      </div>
    );
  }

  if (!schema || schema.questions.length === 0 || schema.sections.length === 0) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-8">
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">
          <ClipboardList className="mx-auto text-slate-600" size={28} />
          <h1 className="mt-3 text-base font-semibold">No intake questions are configured</h1>
          <p className="mt-1 text-sm text-slate-500">
            The backend returned an empty interview. Check its V7 intake configuration.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto min-w-0 max-w-5xl p-4 sm:p-8">
      <div className="mb-6">
        <PageHeader
          title="Business Setup"
          subtitle="Teach the operating system how the business really works. Answers autosave as you move through the interview."
        />

        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-medium text-slate-300">
              {completedCount}/{sectionCount} sections completed
            </span>
            <span className="tabular-nums text-slate-500">
              {requiredAnswered}/{requiredQuestions.length} required answered
            </span>
          </div>
          <div
            className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"
            role="progressbar"
            aria-label="Required intake answers completed"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
          >
            <div
              className="h-full rounded-full bg-violet-500 transition-[width] duration-300 motion-reduce:transition-none"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      <nav aria-label="Business setup steps" className="mb-6 flex flex-wrap gap-2">
        {stepLabels.map((label, index) => {
          const sectionDone = index < sectionCount && completedSectionNames.has(label);
          return (
            <button
              key={`${label}-${index}`}
              type="button"
              onClick={() => void goToStep(index)}
              disabled={saving || reviewRunning || (index === finishStep && uploadsInFlight)}
              aria-current={activeStep === index ? "step" : undefined}
              aria-label={`${label}${sectionDone ? " (completed)" : ""}`}
              className={clsx(
                BUTTON_FOCUS,
                "flex min-h-11 min-w-0 items-center gap-2 rounded-lg border px-3 text-xs transition-colors motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-50",
                activeStep === index
                  ? "border-violet-600 bg-violet-500/15 text-violet-200"
                  : "border-slate-800 bg-slate-900 text-slate-400 hover:border-slate-700 hover:text-slate-200",
              )}
            >
              <span
                className={clsx(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px]",
                  sectionDone ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800",
                )}
              >
                {sectionDone ? <Check size={12} /> : index + 1}
              </span>
              <span className="truncate">{label}</span>
            </button>
          );
        })}
      </nav>

      {activeSection ? (
        <section aria-labelledby="active-section-title" className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
          <div className="mb-5 border-b border-slate-800 pb-4">
            <p className="text-xs font-medium uppercase tracking-wider text-violet-400">
              Section {activeStep + 1} of {sectionCount}
            </p>
            <h2
              ref={stepHeadingRef}
              id="active-section-title"
              tabIndex={-1}
              className="mt-1 text-lg font-semibold outline-none"
            >
              {activeSection}
            </h2>
          </div>

          {activeQuestions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-800 p-6 text-sm text-slate-500">
              This section has no questions yet. You can continue to the next step.
            </div>
          ) : (
            <div className="space-y-4">
              {activeQuestions.map((question) => (
                <QuestionField
                  key={question.key}
                  question={question}
                  value={profile[question.key] ?? ""}
                  disabled={saving}
                  onChange={(value) => updateAnswer(question, value)}
                />
              ))}
            </div>
          )}

          <div className="mt-6 flex flex-col-reverse gap-3 border-t border-slate-800 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <StatusNotice state={saveState} />
            <div className="flex flex-wrap justify-end gap-2">
              {activeStep > 0 && (
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void goToStep(activeStep - 1)}
                  className={clsx(
                    BUTTON_FOCUS,
                    "flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm text-slate-400 hover:text-slate-100 disabled:opacity-50",
                  )}
                >
                  <ArrowLeft size={15} /> Back
                </button>
              )}
              <button
                type="button"
                disabled={saving}
                onClick={() => void saveCurrentSection()}
                className={clsx(
                  BUTTON_FOCUS,
                  "flex min-h-11 items-center gap-2 rounded-lg border border-slate-700 px-4 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50",
                )}
              >
                {saving ? (
                  <Loader2 size={15} className="animate-spin motion-reduce:animate-none" />
                ) : (
                  <Save size={15} />
                )}
                Save
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={() => void goToStep(activeStep + 1)}
                className={clsx(
                  BUTTON_FOCUS,
                  "flex min-h-11 items-center gap-2 rounded-lg bg-violet-600 px-4 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50",
                )}
              >
                Continue <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </section>
      ) : activeStep === uploadStep ? (
        <section aria-labelledby="uploads-title" className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
          <div className="border-b border-slate-800 pb-4">
            <p className="text-xs font-medium uppercase tracking-wider text-violet-400">
              Optional evidence
            </p>
            <h2
              ref={stepHeadingRef}
              id="uploads-title"
              tabIndex={-1}
              className="mt-1 text-lg font-semibold outline-none"
            >
              Upload business material
            </h2>
            <p className="mt-1 text-sm leading-relaxed text-slate-500">
              Add source data or narrative context. CSV files are staged only; nothing is
              imported automatically.
            </p>
          </div>

          {schema.uploads.length === 0 ? (
            <div className="mt-5 rounded-xl border border-dashed border-slate-800 p-6 text-sm text-slate-500">
              No upload types are configured. Continue to finish the interview.
            </div>
          ) : (
            <div className="mt-5 grid min-w-0 gap-4 md:grid-cols-2">
              {schema.uploads.map((upload) => {
                const state = uploadStates[upload.key];
                return (
                  <div key={upload.key} className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex items-start gap-3">
                      <FileUp size={18} className="mt-0.5 shrink-0 text-violet-300" />
                      <div className="min-w-0">
                        <h3 className="text-sm font-medium text-slate-200">{upload.label}</h3>
                        <p className="mt-1 text-xs leading-relaxed text-slate-500">
                          {upload.purpose}
                        </p>
                      </div>
                    </div>
                    <label className="mt-4 block">
                      <span className="sr-only">Choose a file for {upload.label}</span>
                      <input
                        type="file"
                        accept={upload.accepts}
                        disabled={state?.phase === "uploading"}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          event.target.value = "";
                          if (file) void uploadFile(upload, file);
                        }}
                        className={clsx(
                          BUTTON_FOCUS,
                          "block min-h-11 w-full min-w-0 cursor-pointer rounded-lg border border-slate-700 bg-slate-900 text-xs text-slate-400 file:mr-3 file:min-h-11 file:border-0 file:border-r file:border-slate-700 file:bg-slate-800 file:px-3 file:text-xs file:text-slate-200 hover:border-slate-600 disabled:cursor-not-allowed disabled:opacity-50",
                        )}
                      />
                    </label>
                    {state && (
                      <div
                        className={clsx(
                          "mt-3 break-words rounded-lg border p-3 text-xs leading-relaxed",
                          state.phase === "error"
                            ? "border-red-900/70 bg-red-950/30 text-red-300"
                            : state.phase === "success"
                              ? "border-emerald-900/70 bg-emerald-950/30 text-emerald-300"
                              : "border-slate-800 bg-slate-900 text-slate-400",
                        )}
                        role={state.phase === "error" ? "alert" : "status"}
                        aria-live="polite"
                      >
                        <div className="flex items-center gap-2 font-medium">
                          {state.phase === "uploading" ? (
                            <Loader2 size={13} className="animate-spin motion-reduce:animate-none" />
                          ) : state.phase === "success" ? (
                            <CheckCircle2 size={13} />
                          ) : (
                            <CircleAlert size={13} />
                          )}
                          {state.filename}
                        </div>
                        <p className="mt-1">{state.message}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-6 flex flex-wrap justify-end gap-2 border-t border-slate-800 pt-5">
            <button
              type="button"
              onClick={() => void goToStep(sectionCount - 1)}
              className={clsx(
                BUTTON_FOCUS,
                "flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm text-slate-400 hover:text-slate-100",
              )}
            >
              <ArrowLeft size={15} /> Back
            </button>
            <button
              type="button"
              disabled={uploadsInFlight}
              onClick={() => void goToStep(finishStep)}
              className={clsx(
                BUTTON_FOCUS,
                "flex min-h-11 items-center gap-2 rounded-lg bg-violet-600 px-4 text-sm font-medium text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50",
              )}
            >
              {uploadsInFlight ? "Waiting for uploads…" : "Review completeness"}
              {!uploadsInFlight && <ArrowRight size={15} />}
            </button>
          </div>
        </section>
      ) : (
        <section aria-labelledby="finish-title" className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
          <div className="border-b border-slate-800 pb-4">
            <p className="text-xs font-medium uppercase tracking-wider text-violet-400">
              Finish
            </p>
            <h2
              ref={stepHeadingRef}
              id="finish-title"
              tabIndex={-1}
              className="mt-1 text-lg font-semibold outline-none"
            >
              Have the team study the business
            </h2>
            <p className="mt-1 text-sm leading-relaxed text-slate-500">
              The review turns your profile and intake documents into financial, customer,
              and risk memories for future agent work.
            </p>
          </div>

          <div className="mt-5 grid min-w-0 gap-4 lg:grid-cols-[1fr,1.2fr]">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-medium text-slate-200">Interview completeness</h3>
                <span
                  className={clsx(
                    "rounded-full border px-2 py-1 text-xs tabular-nums",
                    requiredComplete
                      ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
                      : "border-amber-800 bg-amber-950/40 text-amber-300",
                  )}
                >
                  {requiredAnswered}/{requiredQuestions.length}
                </span>
              </div>
              {requiredComplete ? (
                <p className="mt-4 flex items-start gap-2 text-sm leading-relaxed text-emerald-300">
                  <CheckCircle2 size={17} className="mt-0.5 shrink-0" /> All required answers
                  are ready.
                </p>
              ) : (
                <div className="mt-4">
                  <p className="text-sm text-amber-300">Complete these required answers:</p>
                  <ul className="mt-2 space-y-2 text-xs leading-relaxed text-slate-400">
                    {missingRequired.map((question) => (
                      <li key={question.key} className="flex gap-2">
                        <span aria-hidden="true">•</span>
                        <span>{question.question}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-violet-900/60 bg-violet-950/20 p-5">
              <div className="flex items-start gap-3">
                <Sparkles size={19} className="mt-0.5 shrink-0 text-violet-300" />
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-violet-100">Analyst review</h3>
                  <p className="mt-1 text-xs leading-relaxed text-violet-200/60">
                    CFO, CMO, and Risk work in parallel. Their report and three memories are
                    saved automatically.
                  </p>
                </div>
              </div>
              <button
                type="button"
                disabled={!requiredComplete || reviewRunning || uploadsInFlight}
                onClick={() => void runReview()}
                className={clsx(
                  BUTTON_FOCUS,
                  "mt-5 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 text-sm font-medium text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {reviewRunning ? (
                  <Loader2 size={16} className="animate-spin motion-reduce:animate-none" />
                ) : (
                  <Sparkles size={16} />
                )}
                {uploadsInFlight
                  ? "Waiting for uploads…"
                  : reviewRunning
                    ? "Team is studying…"
                    : "Have the team study the business"}
              </button>

              {reviewState.phase !== "idle" && (
                <div
                  className={clsx(
                    "mt-4 rounded-lg border p-3 text-xs leading-relaxed",
                    reviewState.phase === "error"
                      ? "border-red-900/70 bg-red-950/30 text-red-300"
                      : reviewState.phase === "success"
                        ? "border-emerald-900/70 bg-emerald-950/30 text-emerald-300"
                        : "border-violet-900/60 bg-slate-950/40 text-violet-200/80",
                  )}
                  role={reviewState.phase === "error" ? "alert" : "status"}
                  aria-live="polite"
                >
                  <div className="flex items-start gap-2">
                    {reviewRunning ? (
                      <Loader2 size={14} className="mt-0.5 shrink-0 animate-spin motion-reduce:animate-none" />
                    ) : reviewState.phase === "success" ? (
                      <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
                    ) : (
                      <CircleAlert size={14} className="mt-0.5 shrink-0" />
                    )}
                    <span>{reviewState.message}</span>
                  </div>
                  {reviewReport && (
                    <div className="mt-3 flex flex-wrap gap-3">
                      <a
                        href={`${API_BASE}/api/reports/${reviewReport.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className={clsx(BUTTON_FOCUS, "font-medium text-emerald-200 underline underline-offset-4")}
                      >
                        Open this review report
                      </a>
                      <Link
                        href="/reports"
                        className={clsx(BUTTON_FOCUS, "text-emerald-300/80 underline underline-offset-4")}
                      >
                        Go to Reports
                      </Link>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm leading-relaxed text-slate-400">
            After the review, agents automatically receive this business profile in chat and
            every venture workflow. Owner estimates remain labeled as assumptions until
            validated.
          </div>

          <div className="mt-6 flex justify-start border-t border-slate-800 pt-5">
            <button
              type="button"
              disabled={reviewRunning}
              onClick={() => void goToStep(uploadStep)}
              className={clsx(
                BUTTON_FOCUS,
                "flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm text-slate-400 hover:text-slate-100 disabled:opacity-50",
              )}
            >
              <ArrowLeft size={15} /> Back to uploads
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
