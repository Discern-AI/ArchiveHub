import type { Dispute } from "../../lib/api";
import type { AttachedRecord } from "../../lib/chat";
import { BasketTab } from "../workspace/BasketTab";
import { EvidenceTab } from "../workspace/EvidenceTab";
import { ExplorerTab } from "../workspace/ExplorerTab";
import { InterviewTab } from "../interview/InterviewTab";
import type { Interview } from "../interview/useInterview";

export type WorkspaceTab = "explorer" | "evidence" | "basket" | "interview";

const TABS: [WorkspaceTab, string][] = [
  ["interview", "Interview"],
  ["explorer", "Explorer"],
  ["evidence", "Evidence"],
  ["basket", "Basket"],
];

/** The right-hand workspace. On phones it takes over the screen. */
export function WorkspacePanel({
  tab,
  onTab,
  onClose,
  projectId,
  dispute,
  onAsk,
  interview,
}: {
  tab: WorkspaceTab;
  onTab: (tab: WorkspaceTab) => void;
  onClose: () => void;
  projectId: string | null;
  dispute: Dispute | null;
  onAsk: (record: AttachedRecord) => void;
  /** Present while an interview is running or has notes to show. */
  interview?: Interview | null;
}) {
  const tabs = TABS.filter(([key]) => key !== "interview" || interview);
  return (
    <aside
      id="workspace-panel"
      aria-label="Workspace"
      className="fixed inset-0 top-[60px] z-20 flex flex-col gap-4 overflow-y-auto border-l border-line bg-surface p-5 md:static md:w-[420px] md:shrink-0"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="m-0 font-serif text-2xl font-semibold">Workspace</h2>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
        >
          Close
        </button>
      </div>
      <div role="tablist" aria-label="Workspace views" className="flex gap-1 border-b border-line">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`ws-tab-${key}`}
            aria-selected={tab === key}
            aria-controls={`ws-panel-${key}`}
            onClick={() => onTab(key)}
            className={`min-h-11 cursor-pointer border-0 border-b-2 bg-transparent px-3 font-medium ${tab === key ? "border-accent text-ink" : "border-transparent text-muted"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`ws-panel-${tab}`} aria-labelledby={`ws-tab-${tab}`}>
        {tab === "interview" && interview && (
          <InterviewTab
            notes={interview.notes}
            sessionId={interview.session?.id ?? null}
            onStatus={interview.setNoteStatus}
          />
        )}
        {tab === "explorer" && <ExplorerTab projectId={projectId} onAsk={onAsk} />}
        {tab === "evidence" && <EvidenceTab dispute={dispute} projectId={projectId} />}
        {tab === "basket" && <BasketTab projectId={projectId} />}
      </div>
    </aside>
  );
}
