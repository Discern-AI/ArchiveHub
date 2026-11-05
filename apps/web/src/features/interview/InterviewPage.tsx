import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { formatTime, interviewApi, type InterviewSession } from "../../lib/interview";

const STATUS: Record<InterviewSession["status"], string> = {
  ready: "Not started",
  recording: "Recording",
  paused: "Paused",
  interrupted: "Stopped early (connection lost)",
  ended: "Ended",
};

function SpeakerEditor({
  sessionId,
  line,
  speaker,
}: {
  sessionId: string;
  line: number;
  speaker: string;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(speaker);
  const save = useMutation({
    mutationFn: () => interviewApi.setSpeaker(sessionId, line, value),
    onSuccess: () => {
      setEditing(false);
      void qc.invalidateQueries({ queryKey: ["interview", sessionId] });
    },
  });
  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        aria-label={`Change speaker for line ${line} (now ${speaker})`}
        className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-left font-semibold text-ink underline decoration-dotted"
      >
        {speaker}
      </button>
    );
  }
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) save.mutate();
      }}
      className="flex flex-wrap items-center gap-2"
    >
      <label className="sr-only" htmlFor={`speaker-${line}`}>
        Speaker for line {line}
      </label>
      <input
        id={`speaker-${line}`}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        maxLength={120}
        className="min-h-11 rounded-lg border border-control px-2"
      />
      <button
        type="submit"
        className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
      >
        Save
      </button>
      <button
        type="button"
        onClick={() => setEditing(false)}
        className="min-h-11 cursor-pointer border-0 bg-transparent px-2 text-accent"
      >
        Cancel
      </button>
    </form>
  );
}

/** An interview's evidence: the original recording, the full transcript and the notes. */
export function InterviewPage() {
  const { interviewId } = useParams();
  const location = useLocation();
  const audio = useRef<HTMLAudioElement>(null);
  const q = useQuery({
    queryKey: ["interview", interviewId],
    queryFn: () => interviewApi.get(interviewId!),
    enabled: !!interviewId,
  });

  // Links like /interviews/<id>#line-4 jump to that line.
  useEffect(() => {
    if (!q.data || !location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView?.({ block: "center" });
  }, [q.data, location.hash]);

  if (q.isPending) return <p className="p-8 text-muted">Loading interview…</p>;
  if (q.isError || !q.data)
    return <p className="p-8 text-warning">Couldn't load this interview.</p>;
  const s = q.data;
  const target = location.hash.match(/^#line-(\d+)$/)?.[1];

  const play = (ms: number) => {
    if (!audio.current) return;
    audio.current.currentTime = ms / 1000;
    void audio.current.play?.();
  };

  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-4 py-8 sm:px-8">
      <header className="flex flex-col gap-1">
        <Link to={`/chat/${s.chat_id}`} className="text-sm">
          ← Back to the chat
        </Link>
        <h1 className="m-0 font-serif text-3xl font-semibold">Interview with {s.narrator}</h1>
        <p className="m-0 text-muted">
          {new Date(s.created_at).toLocaleString("en-GB", {
            dateStyle: "long",
            timeStyle: "short",
          })}
          {" · "}
          {formatTime(s.duration_ms)} · {STATUS[s.status]}
          {s.interviewer && ` · asked by ${s.interviewer}`}
        </p>
      </header>

      <section className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-4">
        <h2 className="m-0 text-lg font-semibold">Original recording</h2>
        {s.has_audio ? (
          <>
            <audio
              ref={audio}
              controls
              preload="metadata"
              src={interviewApi.audioUrl(s.id)}
              className="w-full"
            />
            <p className="m-0 text-[13px] text-muted">
              Kept exactly as recorded (WAV, SHA-256 {s.audio_sha256.slice(0, 12)}…). The transcript
              below was made from it by {s.speech_engine || "speech recognition"}.
            </p>
          </>
        ) : (
          <p className="m-0 text-muted">No recording was saved.</p>
        )}
        <p className="m-0 text-[13px] text-muted">
          Consent confirmed{" "}
          {new Date(s.consent_confirmed_at).toLocaleString("en-GB", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
          : “{s.consent_notice}”
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="m-0 text-lg font-semibold">Transcript</h2>
        <p className="m-0 text-sm text-muted">
          Made by speech recognition and not corrected. Listen to the recording to check a line.
          Select a speaker's name to change it.
        </p>
        {s.segments?.length === 0 && <p className="text-muted">No speech was picked up.</p>}
        <ol className="m-0 flex list-none flex-col gap-1 p-0">
          {s.segments?.map((g) => (
            <li
              key={g.line}
              id={`line-${g.line}`}
              className={`grid grid-cols-[3rem_1fr] gap-x-3 rounded-lg p-2 ${String(g.line) === target ? "bg-selected" : ""}`}
            >
              <span className="pt-2.5 text-sm text-muted">{g.line}</span>
              <div className="flex flex-col">
                <div className="flex flex-wrap items-center gap-x-3">
                  <SpeakerEditor sessionId={s.id} line={g.line} speaker={g.speaker} />
                  {s.has_audio && (
                    <button
                      type="button"
                      onClick={() => play(g.start_ms)}
                      aria-label={`Play line ${g.line} from ${formatTime(g.start_ms)}`}
                      className="min-h-11 cursor-pointer border-0 bg-transparent px-1 text-sm text-accent"
                    >
                      ▶ {formatTime(g.start_ms)}
                    </button>
                  )}
                </div>
                <p className="m-0">{g.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {s.notes && s.notes.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="m-0 text-lg font-semibold">Picked up by the assistant</h2>
          <p className="m-0 text-sm text-muted">
            Interpretation, not evidence: each item points at the lines it came from.
          </p>
          <ul className="m-0 flex flex-col gap-1 pl-5">
            {s.notes
              .filter((n) => n.status !== "dismissed")
              .map((n) => (
                <li key={n.id}>
                  <span className="text-muted">
                    {n.kind === "question" ? "Question" : n.kind[0].toUpperCase() + n.kind.slice(1)}
                    :
                  </span>{" "}
                  {n.text}
                  {n.detail && ` (${n.detail})`}{" "}
                  {n.lines.map((l) => (
                    <a key={l} href={`#line-${l}`} className="mr-1 text-sm">
                      line {l}
                    </a>
                  ))}
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}
