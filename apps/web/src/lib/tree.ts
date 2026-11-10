/** Family tree tools: imports with a preview, updates from a new export, and undo. */
import { request, type Job } from "./api";

export interface ImportedTree {
  tree: string;
  first_file: string;
  people: number;
  last_updated: string | null;
  last_file: string;
}

export interface HealthFinding {
  kind: "dates" | "parents" | "duplicates" | "branches" | "gaps";
  title: string;
  detail: string;
  people: { id: string; name: string }[];
}

export interface ImportPreview {
  people: number;
  families: number;
  living_private: number;
  mode: "new" | "update";
  added: number;
  updated: number;
  not_in_file: string[];
  not_in_file_count: number;
  id_but_not_name: { id: string; in_tree: string; in_file: string }[];
  report: Record<string, unknown>;
  health: { findings: HealthFinding[] };
}

export interface Change {
  id: string;
  kind: "import" | "update" | "merge" | "delete";
  summary: string;
  created_at: string;
  by: string;
  undone_at: string | null;
  counts: Record<string, number>;
  blocked: string[];
}

export const treeApi = {
  trees: (projectId: string) =>
    request<ImportedTree[]>("GET", `/api/v1/projects/${projectId}/trees`),
  preview: (fileId: string, mode: "new" | "update", base: string) =>
    request<ImportPreview>(
      "GET",
      `/api/v1/files/${fileId}/gedcom-preview?mode=${mode}&base=${encodeURIComponent(base)}`,
    ),
  importTree: (fileId: string, mode: "new" | "update", base: string) =>
    request<Job>("POST", `/api/v1/files/${fileId}/jobs`, {
      kind: "gedcom_import",
      options: mode === "update" ? { mode, base } : {},
    }),
  changes: (projectId: string) => request<Change[]>("GET", `/api/v1/projects/${projectId}/changes`),
  undo: (projectId: string, changeId: string) =>
    request<Change>("POST", `/api/v1/projects/${projectId}/changes/${changeId}/undo`),
};
