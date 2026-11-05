import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type DragEvent, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { api, archiveApi, uploadFile, type ArchiveFile } from "../../lib/api";
import { FileDetail } from "./FileDetail";

const STATUS: Record<string, string> = {
  uploaded: "Uploaded",
  checked: "Reading…",
  indexed: "Read",
  needs_processing: "Ready to process",
  failed: "Couldn't be read",
  rejected: "Rejected",
};

function size(bytes: number) {
  return bytes > 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${Math.ceil(bytes / 1e3)} KB`;
}

export function ArchivePage() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const projectId = params.get("project") ?? projects.data?.[0]?.id ?? null;
  const [folderId, setFolderId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newFolder, setNewFolder] = useState("");

  const folders = useQuery({
    queryKey: ["folders", projectId],
    queryFn: () => archiveApi.folders(projectId!),
    enabled: !!projectId,
  });
  const files = useQuery({
    queryKey: ["files", projectId, folderId],
    queryFn: () => archiveApi.files(projectId!, folderId),
    enabled: !!projectId,
    // Keep checking while files are still being read.
    refetchInterval: (q) =>
      (q.state.data as ArchiveFile[] | undefined)?.some((f) => f.status === "checked")
        ? 1500
        : false,
  });

  async function upload(list: FileList | null) {
    if (!projectId || !list?.length) return;
    setBusy(true);
    setMessage(null);
    const problems: string[] = [];
    for (const file of Array.from(list)) {
      try {
        await uploadFile(projectId, file, folderId);
      } catch (err) {
        problems.push(`${file.name}: ${(err as Error).message}`);
      }
    }
    setBusy(false);
    setMessage(
      problems.length ? problems.join(" ") : `Added ${list.length} file(s). They're private.`,
    );
    await qc.invalidateQueries({ queryKey: ["files", projectId] });
  }

  async function addFolder(e: FormEvent) {
    e.preventDefault();
    if (!projectId || !newFolder.trim()) return;
    const f = await archiveApi.createFolder(projectId, newFolder);
    setNewFolder("");
    await qc.invalidateQueries({ queryKey: ["folders", projectId] });
    setFolderId(f.id);
  }

  if (projects.isPending) return <p className="p-8 text-muted">Loading…</p>;
  if (!projectId) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-12">
        <h1 className="m-0 font-serif text-[34px] font-semibold">Archive</h1>
        <p className="text-muted">
          Files live in a project. <Link to="/projects/new">Create a project</Link> first.
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="mx-auto flex w-full max-w-[1120px] min-w-0 flex-col gap-4 px-4 py-8 sm:px-12">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="m-0 font-serif text-[34px] font-semibold">Archive</h1>
            <p className="mt-1 mb-0 text-muted">
              Private unless you publish them. Reading handwriting or scans uses credits, and we
              always ask first.
            </p>
          </div>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Project
            <select
              value={projectId}
              onChange={(e) => {
                setParams({ project: e.target.value });
                setFolderId(null);
                setSelected(null);
              }}
              className="min-h-11 rounded-lg border border-control bg-surface px-2 font-normal"
            >
              {projects.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div
          onDragOver={(e: DragEvent) => e.preventDefault()}
          onDrop={(e: DragEvent) => {
            e.preventDefault();
            upload(e.dataTransfer.files);
          }}
          className="flex flex-wrap items-center justify-center gap-3 rounded-lg border-2 border-dashed border-control bg-surface p-5"
        >
          <span>Drag files here, or</span>
          <input
            id="archive-upload"
            type="file"
            multiple
            className="sr-only"
            onChange={(e) => upload(e.target.files)}
          />
          <label
            htmlFor="archive-upload"
            className="flex min-h-11 cursor-pointer items-center rounded-lg bg-accent px-4 font-semibold text-white"
          >
            {busy ? "Uploading…" : "Choose files"}
          </label>
          <span className="w-full text-center text-[13px] text-muted">
            PDF, images, Word, text, family tree (.ged), audio and video. Up to 50 MB each.
          </span>
        </div>
        {message && (
          <p role="status" className="m-0 text-sm font-medium">
            {message}
          </p>
        )}

        <div className="flex flex-wrap items-start gap-5">
          <div role="group" aria-label="Folders" className="flex w-full flex-col gap-0.5 sm:w-48">
            {[{ id: null, name: "All files" }, ...(folders.data ?? [])].map((f) => (
              <button
                key={f.id ?? "all"}
                type="button"
                aria-pressed={folderId === f.id}
                onClick={() => setFolderId(f.id)}
                className={`min-h-11 cursor-pointer rounded-lg px-2.5 text-left ${folderId === f.id ? "bg-tint-strong font-semibold" : "bg-transparent"}`}
              >
                {f.name}
              </button>
            ))}
            <form onSubmit={addFolder} className="mt-2 flex gap-1">
              <label htmlFor="new-folder" className="sr-only">
                New folder name
              </label>
              <input
                id="new-folder"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                placeholder="New folder"
                className="min-h-11 min-w-0 flex-1 rounded-lg border border-control px-2"
              />
              <button
                type="submit"
                className="min-h-11 cursor-pointer rounded-lg border border-control px-2"
              >
                Add
              </button>
            </form>
            <Link to={`/projects/${projectId}/people`} className="mt-3 min-h-11 px-2.5">
              Family tree →
            </Link>
          </div>

          <div className="min-w-0 flex-1 overflow-x-auto rounded-lg border border-line bg-surface">
            <table className="w-full min-w-[520px] border-collapse">
              <thead>
                <tr className="text-left text-[13px] text-muted">
                  <th scope="col" className="border-b border-line p-3">
                    Name
                  </th>
                  <th scope="col" className="border-b border-line p-3">
                    Type
                  </th>
                  <th scope="col" className="border-b border-line p-3">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {files.data?.length === 0 && (
                  <tr>
                    <td colSpan={3} className="p-4 text-muted">
                      No files here yet.
                    </td>
                  </tr>
                )}
                {files.data?.map((f) => (
                  <tr key={f.id} className={selected === f.id ? "bg-selected" : ""}>
                    <td className="border-b border-line-soft px-3 py-1">
                      <button
                        type="button"
                        onClick={() => setSelected(f.id)}
                        className="min-h-11 cursor-pointer bg-transparent text-left font-medium underline"
                      >
                        {f.name}
                      </button>
                    </td>
                    <td className="border-b border-line-soft px-3 text-sm">
                      {f.kind} · {size(f.size)}
                    </td>
                    <td className="border-b border-line-soft px-3 text-sm">
                      {STATUS[f.status] ?? f.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {selected && (
        <FileDetail
          fileId={selected}
          projectId={projectId}
          onClose={() => setSelected(null)}
          onDeleted={() => {
            setSelected(null);
            qc.invalidateQueries({ queryKey: ["files", projectId] });
          }}
        />
      )}
    </div>
  );
}
