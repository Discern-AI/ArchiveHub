/** Life Story and galleries. */
import { request } from "./api";

export interface StorySource {
  title: string;
  url: string;
  source: string;
  what_it_says: string;
}

export interface StoryEvent {
  chapter: string;
  year: number | null;
  kind: string;
  sentence: string;
  status: "documented" | "remembered" | "inferred" | "disputed";
  claim_ids: string[];
  sources: StorySource[];
  people: { id: string; name: string }[];
}

export interface LifeStory {
  person: { id: string; name: string };
  private: boolean;
  note?: string;
  at_a_glance?: {
    born: string;
    died: string;
    occupation: string;
    partners: number;
    children: number;
  };
  chapters?: { key: string; title: string; events: StoryEvent[] }[];
  context?: {
    title: string;
    date_text: string;
    area: string;
    age: string;
    source_title: string;
    source_url: string;
  }[];
  context_note?: string;
  gaps?: string[];
}

export type Relation = "shows" | "about" | "context";

export interface GalleryItem {
  id: string;
  file_id: string;
  file_name: string;
  has_preview: boolean;
  caption: string;
  date_text: string;
  year: number | null;
  decade: string;
  place_text: string;
  relation: Relation | null;
  people: { id: string; name: string; relation: Relation }[];
}

export interface PhotoSuggestion {
  file_id: string;
  file_name: string;
  folder: string;
  has_preview: boolean;
  year_hint: number | null;
  year_from: string;
  suggestions: { id: string; name: string; score: number; reason: string }[];
}

export const RELATION_LABEL: Record<Relation, string> = {
  shows: "Shows them",
  about: "About them",
  context: "Their world, not them",
};

const base = (p: string) => `/api/v1/projects/${p}`;

export const storyApi = {
  lifeStory: (p: string, person: string) =>
    request<LifeStory>("GET", `${base(p)}/people/${person}/life-story`),
  gallery: (p: string, person: string) =>
    request<GalleryItem[]>("GET", `${base(p)}/people/${person}/gallery`),
  familyGallery: (p: string) => request<GalleryItem[]>("GET", `${base(p)}/gallery`),
  add: (
    p: string,
    body: {
      file_id: string;
      caption?: string;
      date_text?: string;
      place_text?: string;
      tags: { person_id: string; relation: Relation }[];
    },
  ) => request<GalleryItem>("POST", `${base(p)}/gallery`, body),
  edit: (
    p: string,
    item: string,
    body: { caption?: string; date_text?: string; place_text?: string },
  ) => request<GalleryItem>("PATCH", `${base(p)}/gallery/${item}`, body),
  untag: (p: string, item: string, person: string) =>
    request<void>("DELETE", `${base(p)}/gallery/${item}/tags/${person}`),
  remove: (p: string, item: string) => request<void>("DELETE", `${base(p)}/gallery/${item}`),
  order: (p: string, person: string, itemIds: string[]) =>
    request<GalleryItem[]>("PUT", `${base(p)}/people/${person}/gallery/order`, {
      item_ids: itemIds,
    }),
  suggestions: (p: string) => request<PhotoSuggestion[]>("GET", `${base(p)}/photo-suggestions`),
};
