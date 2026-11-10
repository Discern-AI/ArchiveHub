import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { api } from "../../lib/api";

export function NewProjectPage() {
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Give your project a name.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const project = await api.createProject(title, summary);
      await qc.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="mx-auto flex w-full max-w-[640px] flex-col gap-4 px-4 py-10 sm:px-12"
    >
      <h1 className="m-0 font-serif text-[34px] font-semibold">New project</h1>
      <p className="m-0 text-muted">
        A project keeps related chats together, such as one family, one building or one pub. It's
        private to you.
      </p>
      <label className="flex flex-col gap-1 font-medium">
        Name
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="For example: The Carter family, or the pubs of our high street"
          className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
        />
      </label>
      <label className="flex flex-col gap-1 font-medium">
        What it's about (optional)
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={3}
          className="rounded-lg border border-control bg-surface p-3 font-normal"
        />
      </label>
      {error && (
        <p role="alert" className="m-0 font-medium text-warning">
          {error}
        </p>
      )}
      <div>
        <button
          type="submit"
          disabled={saving}
          className="min-h-11 cursor-pointer rounded-lg bg-accent px-5 font-semibold text-white disabled:opacity-60"
        >
          {saving ? "Creating…" : "Create project"}
        </button>
      </div>
    </form>
  );
}
