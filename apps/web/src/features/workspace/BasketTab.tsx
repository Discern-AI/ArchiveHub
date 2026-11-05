import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";

const STORAGE: Record<string, string> = {
  full_copy: "Copy kept",
  reference_only: "Link and our notes only",
  metadata_only: "Catalogue details only",
};

export function BasketTab({ projectId }: { projectId: string | null }) {
  const qc = useQueryClient();
  const basket = useQuery({
    queryKey: ["basket", projectId],
    queryFn: () => api.basket(projectId!),
    enabled: !!projectId,
  });

  if (!projectId) {
    return (
      <p className="m-0 text-muted">
        The research basket belongs to a project. Start this chat from a project to save records.
      </p>
    );
  }
  if (basket.isPending) return <p className="m-0 text-muted">Loading…</p>;
  if (basket.isError) return <p className="m-0 text-warning">Couldn't load the basket.</p>;
  if (!basket.data.length) {
    return <p className="m-0 text-muted">Nothing saved yet. Use the Explorer to save records.</p>;
  }

  return (
    <ul aria-label="Saved records" className="m-0 flex list-none flex-col gap-2 p-0">
      {basket.data.map((item) => (
        <li key={item.id} className="flex flex-col gap-1 rounded-lg border border-line p-3">
          {item.url ? (
            <a href={item.url} target="_blank" rel="noreferrer" className="font-semibold">
              {item.title}
            </a>
          ) : (
            <strong>{item.title}</strong>
          )}
          <span className="text-[13px] text-muted">{STORAGE[item.storage] ?? item.storage}</span>
          <div>
            <button
              type="button"
              onClick={async () => {
                await api.removeFromBasket(projectId, item.id);
                await qc.invalidateQueries({ queryKey: ["basket", projectId] });
              }}
              className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 text-sm"
            >
              Remove
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
