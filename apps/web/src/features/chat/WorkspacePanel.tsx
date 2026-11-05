/** The right-hand workspace. On phones it takes over the screen. */
export function WorkspacePanel({ onClose }: { onClose: () => void }) {
  return (
    <aside
      id="workspace-panel"
      aria-label="Workspace"
      className="fixed inset-0 top-[60px] z-20 flex flex-col gap-4 overflow-y-auto border-l border-line bg-surface p-6 md:static md:w-[380px] md:shrink-0"
    >
      <h2 className="m-0 font-serif text-2xl font-semibold">Workspace</h2>
      <p className="m-0 text-muted">
        Evidence comparisons, drafts, family trees, interview prompts and the Archive Explorer will
        open here as they arrive.
      </p>
      <button
        type="button"
        onClick={onClose}
        className="mt-auto min-h-11 cursor-pointer rounded-lg border border-control bg-surface"
      >
        Close workspace
      </button>
    </aside>
  );
}
