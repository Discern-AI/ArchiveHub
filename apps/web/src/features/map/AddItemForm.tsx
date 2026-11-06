import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { api, archiveApi } from "../../lib/api";
import { mapApi, type MapFeature, type NewMapItem } from "../../lib/map";
import type { View } from "./MapView";

const field = "min-h-11 rounded-lg border border-control bg-surface px-2 font-normal";
const KINDS: [NewMapItem["kind"], string][] = [
  ["memory", "A memory"],
  ["photo", "A photo from the Archive"],
  ["document", "A document from the Archive"],
];

function yearOrNull(text: string): number | null {
  const n = Number(text);
  return text.trim() && Number.isInteger(n) ? n : null;
}

export function AddItemForm({
  point,
  view,
  onUseCentre,
  onCancel,
  onAdded,
}: {
  point: { lat: number; lng: number } | null;
  view: View;
  onUseCentre: (p: { lat: number; lng: number }) => void;
  onCancel: () => void;
  onAdded: (f: MapFeature) => void;
}) {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [projectId, setProjectId] = useState<string>("");
  const pid = projectId || projects.data?.[0]?.id || "";
  const [kind, setKind] = useState<NewMapItem["kind"]>("memory");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [fileId, setFileId] = useState("");
  const [dateText, setDateText] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [dateRole, setDateRole] = useState<"event" | "made">("event");
  const [locationNote, setLocationNote] = useState("");
  const [precision, setPrecision] = useState("inferred");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const files = useQuery({
    queryKey: ["files", pid, null],
    queryFn: () => archiveApi.files(pid),
    enabled: !!pid && kind !== "memory",
  });
  const choosable = (files.data ?? []).filter((f) =>
    kind === "photo" ? f.kind === "image" : f.kind !== "image",
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!point) {
      setError("Click the map where it belongs first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const from = yearOrNull(yearFrom);
      const f = await mapApi.addItem(pid, {
        kind,
        title,
        text,
        latitude: point.lat,
        longitude: point.lng,
        location_note: locationNote,
        precision,
        date_text: dateText,
        year_from: from,
        year_to: yearOrNull(yearTo) ?? from,
        date_role: dateRole,
        file_id: kind === "memory" ? null : fileId || null,
      });
      onAdded(f);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (projects.data && projects.data.length === 0) {
    return (
      <div className="flex flex-col gap-2">
        <p className="m-0">
          Memories and photos live in a project. <Link to="/projects/new">Create a project</Link>{" "}
          first.
        </p>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
        >
          Cancel
        </button>
      </div>
    );
  }

  const projectTitle = projects.data?.find((p) => p.id === pid)?.title ?? "your project";
  return (
    <form onSubmit={submit} className="flex flex-col gap-3" aria-label="Add to the map">
      <h2 className="m-0 font-serif text-2xl font-semibold">Add to the map</h2>
      <p className="m-0 rounded-lg bg-private-tint p-3 text-sm">
        <strong>Private to {projectTitle}.</strong> Only people in this project can see it.
      </p>
      <p className={`m-0 text-sm ${point ? "" : "font-semibold text-accent"}`} aria-live="polite">
        {point
          ? `Location chosen (${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}). Click the map again to move it.`
          : "Click the map where it belongs."}
      </p>
      <button
        type="button"
        onClick={() => onUseCentre({ lat: view.lat, lng: view.lng })}
        className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3 text-sm"
      >
        Use the middle of the map
      </button>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Project
        <select value={pid} onChange={(e) => setProjectId(e.target.value)} className={field}>
          {projects.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
        <legend className="mb-1 text-sm font-medium">What is it?</legend>
        {KINDS.map(([k, label]) => (
          <label key={k} className="flex min-h-11 items-center gap-2">
            <input
              type="radio"
              name="kind"
              checked={kind === k}
              onChange={() => setKind(k)}
              className="size-5"
            />
            {label}
          </label>
        ))}
      </fieldset>
      {kind !== "memory" && (
        <label className="flex flex-col gap-1 text-sm font-medium">
          File
          <select
            value={fileId}
            onChange={(e) => setFileId(e.target.value)}
            className={field}
            required
          >
            <option value="">Choose a file</option>
            {choosable.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          {files.data && choosable.length === 0 && (
            <span className="font-normal text-muted">
              No {kind === "photo" ? "photos" : "documents"} in this project yet. Add them in the{" "}
              <Link to={`/archive?project=${pid}`}>Archive</Link>.
            </span>
          )}
        </label>
      )}
      <label className="flex flex-col gap-1 text-sm font-medium">
        Title
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={field}
          required
          maxLength={200}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        {kind === "memory" ? "The memory, in your own words" : "Notes (optional)"}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          required={kind === "memory"}
          className="rounded-lg border border-control bg-surface p-2 font-normal"
        />
      </label>
      <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
        <legend className="mb-1 text-sm font-medium">Which date is this?</legend>
        <label className="flex min-h-11 items-center gap-2">
          <input
            type="radio"
            name="role"
            checked={dateRole === "event"}
            onChange={() => setDateRole("event")}
            className="size-5"
          />
          When it happened
        </label>
        <label className="flex min-h-11 items-center gap-2">
          <input
            type="radio"
            name="role"
            checked={dateRole === "made"}
            onChange={() => setDateRole("made")}
            className="size-5"
          />
          When the photo was taken or the document written
        </label>
      </fieldset>
      <div className="flex flex-wrap gap-2">
        <label className="flex w-28 flex-col gap-1 text-sm font-medium">
          From year
          <input
            inputMode="numeric"
            value={yearFrom}
            onChange={(e) => setYearFrom(e.target.value)}
            className={field}
          />
        </label>
        <label className="flex w-28 flex-col gap-1 text-sm font-medium">
          To year
          <input
            inputMode="numeric"
            value={yearTo}
            onChange={(e) => setYearTo(e.target.value)}
            className={field}
          />
        </label>
        <label className="flex min-w-40 flex-1 flex-col gap-1 text-sm font-medium">
          Date as you'd say it
          <input
            value={dateText}
            onChange={(e) => setDateText(e.target.value)}
            placeholder="e.g. summer 1952"
            className={field}
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Where exactly? (optional)
        <input
          value={locationNote}
          onChange={(e) => setLocationNote(e.target.value)}
          placeholder="e.g. the corner shop opposite the Pigeons"
          className={field}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        How sure is the location?
        <select value={precision} onChange={(e) => setPrecision(e.target.value)} className={field}>
          <option value="exact">This exact spot</option>
          <option value="street">Somewhere on this street</option>
          <option value="town">Somewhere in the town</option>
          <option value="inferred">A rough guess</option>
        </select>
      </label>
      {error && <p className="m-0 text-warning">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy}
          className="min-h-11 cursor-pointer rounded-lg border-0 bg-accent px-4 font-medium text-white disabled:opacity-60"
        >
          {busy ? "Adding…" : "Add to the map"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
