import { ImportReport } from "./ImportReport";
import { ImportTree } from "./ImportTree";
import { ExplainRecord } from "../explain/ExplainRecord";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { archiveApi, type ArchiveFileDetail, type Job } from "../../lib/api";

const METHOD: Record<string, string> = {
  plain_text: "Text as uploaded",
  pdf_text: "Text from the PDF",
  docx_text: "Text from the Word document",
  gedcom_text: "Family tree file",
  ocr: "Printed text read by OCR",
  ai_handwriting: "Handwriting read by AI",
};

const JOB_STATUS: Record<Job["status"], string> = {
  awaiting_confirmation: "Waiting for your go-ahead",
  queued: "Queued",
  running: "Running",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

const active = (d?: ArchiveFileDetail) =>
  !!d &&
  (d.status === "checked" || d.jobs.some((j) => j.status === "queued" || j.status === "running"));

export function FileDetail({
  fileId,
  projectId,
  onClose,
  onDeleted,
}: {
  fileId: string;
  projectId: string;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => archiveApi.file(fileId),
    refetchInterval: (q) => (active(q.state.data as ArchiveFileDetail | undefined) ? 1500 : false),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["file", fileId] });
    qc.invalidateQueries({ queryKey: ["files", projectId] });
  };

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const d = detail.data;
  const waiting = d?.jobs.find((j) => j.status === "awaiting_confirmation");
  const imported = d?.jobs.some((j) => j.kind === "gedcom_import" && j.status === "done");

  return (
    <aside
      aria-label="File details"
      className="fixed inset-0 top-[60px] z-20 flex flex-col gap-3 overflow-y-auto border-l border-line bg-surface p-5 md:static md:w-[420px] md:shrink-0"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="m-0 truncate font-serif text-xl font-semibold">{d?.name ?? "File"}</h2>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 cursor-pointer rounded-lg border border-control px-3"
        >
          Close
        </button>
      </div>
      {detail.isPending && <p className="m-0 text-muted">Loading…</p>}
      {d && (
        <>
          {d.has_preview && (
            <img
              src={`/api/v1/files/${d.id}/preview`}
              alt={`Preview of ${d.name}`}
              className="max-h-72 w-full rounded-lg bg-tint object-contain"
            />
          )}
          {d.status_detail && <p className="m-0">{d.status_detail}</p>}
          <p className="m-0 text-[13px] text-muted">{d.scan_note}</p>

          {d.can_process.some((p) => p.kind === "gedcom_import") && !waiting && (
            <ImportTree fileId={d.id} projectId={projectId} onImported={refresh} />
          )}
          {d.can_process.some((p) => p.kind !== "gedcom_import") && !waiting && (
            <div className="flex flex-wrap gap-2">
              {d.can_process
                .filter((p) => p.kind !== "gedcom_import")
                .map((p) => (
                  <button
                    key={p.kind}
                    type="button"
                    onClick={() => run(() => archiveApi.requestJob(d.id, p.kind))}
                    className="min-h-11 cursor-pointer rounded-lg border border-accent bg-surface px-3 font-medium text-accent"
                  >
                    {p.label}
                  </button>
                ))}
            </div>
          )}

          {waiting && (
            <section
              role="alertdialog"
              aria-label="Confirm credit use"
              className="flex flex-col gap-2 rounded-lg border-2 border-warning p-3"
            >
              <strong>
                {waiting.kind === "handwriting"
                  ? "Read the handwriting in this file?"
                  : "Read the printed text in this file?"}
              </strong>
              <span>
                This is estimated to use about {waiting.estimate_credits} credits. The original file
                stays unchanged.
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => run(() => archiveApi.cancelJob(waiting.id))}
                  className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
                >
                  Not now
                </button>
                <button
                  type="button"
                  onClick={() => run(() => archiveApi.confirmJob(waiting.id))}
                  className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
                >
                  Use credits and start
                </button>
              </div>
            </section>
          )}

          {imported && (
            <Link to={`/projects/${projectId}/people`} className="font-semibold">
              Open the family tree →
            </Link>
          )}
          {d.jobs
            .filter((j) => j.kind === "gedcom_import" && j.status === "done")
            .slice(0, 1)
            .map((j) => (
              <ImportReport key={j.id} result={j.result} projectId={projectId} onUndone={refresh} />
            ))}

          {d.jobs.length > 0 && (
            <ul aria-label="Processing" className="m-0 flex list-none flex-col gap-1 p-0 text-sm">
              {d.jobs.map((j) => (
                <li key={j.id}>
                  <strong>{j.kind.replace("_", " ")}:</strong> {JOB_STATUS[j.status]}
                  {j.error && <span className="text-warning"> — {j.error}</span>}
                </li>
              ))}
            </ul>
          )}

          {d.texts.length > 0 && d.kind !== "gedcom" && (
            <ExplainFile key={d.id} text={d.texts[0].text} />
          )}
          {d.texts.map((t) => (
            <section key={t.id} className="flex flex-col gap-1">
              <h3 className="m-0 text-base font-semibold">{METHOD[t.method] ?? t.method}</h3>
              {t.note && <p className="m-0 text-[13px] font-medium text-warning">{t.note}</p>}
              <pre className="m-0 max-h-80 overflow-auto rounded-lg bg-tint p-3 text-sm whitespace-pre-wrap">
                {t.text}
              </pre>
            </section>
          ))}

          <a href={`/api/v1/files/${d.id}/original`} className="font-semibold">
            Download the original
          </a>
          <p className="m-0 text-[13px] break-all text-muted">Checksum (SHA-256): {d.sha256}</p>

          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="min-h-11 cursor-pointer self-start rounded-lg border border-warning bg-surface px-3 text-warning"
            >
              Delete file…
            </button>
          ) : (
            <div
              role="alertdialog"
              aria-label="Confirm deletion"
              className="flex flex-col gap-2 rounded-lg border-2 border-warning p-3"
            >
              <span>
                Delete <strong>{d.name}</strong> and everything read from it? This can't be undone.
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="min-h-11 cursor-pointer rounded-lg border border-control px-3"
                >
                  Keep it
                </button>
                <button
                  type="button"
                  onClick={() =>
                    run(async () => {
                      await archiveApi.deleteFile(d.id);
                      onDeleted();
                    })
                  }
                  className="min-h-11 cursor-pointer rounded-lg bg-warning px-3 font-semibold text-white"
                >
                  Delete file
                </button>
              </div>
            </div>
          )}
          {error && (
            <p role="alert" className="m-0 font-medium text-warning">
              {error}
            </p>
          )}
        </>
      )}
    </aside>
  );
}

/** Built only when opened, so the file's text isn't on the page twice. */
function ExplainFile({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded-lg border border-line p-3">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-medium text-accent"
      >
        {open ? "Close the explanation" : "Explain this record"}
      </button>
      {open && <ExplainRecord initialText={text.slice(0, 1500)} />}
    </section>
  );
}
