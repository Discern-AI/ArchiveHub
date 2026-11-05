import { Link } from "react-router";
import { formatTime } from "../../lib/interview";
import type { Interview } from "./useInterview";

const button =
  "min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-4 font-medium disabled:cursor-not-allowed disabled:opacity-50";

/**
 * The bottom bar during an interview. Live words stay in place here; each finished line
 * lifts out of the bar and fades as it rises, while the same line settles into the chat.
 */
export function InterviewBar({ interview }: { interview: Interview }) {
  const { phase, partial, lines, elapsedMs, session, notice, error } = interview;
  const last = lines[lines.length - 1];
  const live = phase === "recording" || phase === "paused";

  return (
    <section
      aria-label="Interview"
      className="mx-auto flex w-full max-w-[760px] flex-col gap-2 rounded-xl border border-control bg-surface p-3"
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex items-center gap-2 font-semibold" role="status">
          {phase === "recording" && (
            <span aria-hidden="true" className="ah-pulse size-3 rounded-full bg-live" />
          )}
          {phase === "connecting" && "Getting ready…"}
          {phase === "recording" && `Recording ${formatTime(elapsedMs)}`}
          {phase === "paused" && `Paused at ${formatTime(elapsedMs)}`}
          {phase === "ending" && "Finishing the last words…"}
          {phase === "sending" && "Sending to the chat…"}
          {phase === "interrupted" && "Interview stopped"}
        </span>
        {session && <span className="text-sm text-muted">with {session.narrator}</span>}
        <span className="flex-1" />
        {phase === "recording" && (
          <button type="button" onClick={interview.pause} className={button}>
            Pause
          </button>
        )}
        {phase === "paused" && (
          <button type="button" onClick={interview.resume} className={button}>
            Resume
          </button>
        )}
        {live && (
          <button
            type="button"
            onClick={interview.end}
            className="min-h-11 cursor-pointer rounded-lg border-0 bg-accent px-4 font-semibold text-white"
          >
            End and send
          </button>
        )}
        {phase === "interrupted" && session && (
          <>
            <Link to={`/interviews/${session.id}`} className="text-sm">
              Open recording
            </Link>
            <button type="button" onClick={interview.reset} className={button}>
              Close
            </button>
            {!session.sent && (
              <button
                type="button"
                onClick={() => void interview.retrySend()}
                className="min-h-11 cursor-pointer rounded-lg border-0 bg-accent px-4 font-semibold text-white"
              >
                Send what was recorded
              </button>
            )}
          </>
        )}
        {phase === "interrupted" && !session && (
          <button type="button" onClick={interview.reset} className={button}>
            Close
          </button>
        )}
      </div>

      {/* Live words: provisional, so not announced word by word to screen readers. */}
      <div className="relative min-h-[3.25rem] overflow-visible" aria-live="off">
        {last && live && (
          <p
            key={last.line}
            aria-hidden="true"
            className="ah-rise pointer-events-none absolute inset-x-0 top-0 m-0 text-lg"
          >
            {last.text}
          </p>
        )}
        <p className="m-0 text-lg text-muted">
          {partial ||
            (phase === "recording"
              ? lines.length
                ? ""
                : "Start talking whenever you're ready."
              : phase === "paused"
                ? "Nothing is recorded while paused."
                : "")}
        </p>
      </div>

      {notice && <p className="m-0 text-sm text-warning">{notice}</p>}
      {error && (
        <p role="alert" className="m-0 text-sm font-medium text-warning">
          {error}
        </p>
      )}
    </section>
  );
}
