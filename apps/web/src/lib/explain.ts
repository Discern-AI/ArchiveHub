/** Explain this record, Life and times, and offering explanations. */
import { request } from "./api";

export interface Src {
  title: string;
  url: string;
}

export interface Explained {
  says: { text: string; year: number | null; place: string };
  words: {
    term: string;
    found: string;
    meaning: string;
    area: string;
    applies: boolean;
    period_note: string;
    sources: Src[];
    contributed_by: string;
  }[];
  may_mean: { term: string; text: string; sources: Src[] }[];
  may_mean_label: string;
  find_out_more: { text: string; sources: Src[] }[];
  sensitive: boolean;
  sensitive_note: string;
  nothing_found: boolean;
  note: string;
}

export interface LifeAndTimes {
  year: number;
  label: string;
  money: {
    available: boolean;
    note: string;
    sentence?: string;
    source?: string;
    source_url?: string;
  };
  weather: {
    available: boolean;
    note: string;
    sentence?: string;
    rank?: string;
    source?: string;
    source_url?: string;
  };
  happening: {
    title: string;
    date_text: string;
    area: string;
    kind: string;
    when: string;
    source_title: string;
    source_url: string;
  }[];
  accounts: { available: boolean; note: string; search: string };
}

export const explainApi = {
  explain: (body: { text: string; year?: number | null; place?: string }) =>
    request<Explained>("POST", "/api/v1/explain", body),
  lifeAndTimes: (year: number, projectId?: string) =>
    request<LifeAndTimes>(
      "GET",
      `/api/v1/life-and-times?year=${year}${projectId ? `&project_id=${projectId}` : ""}`,
    ),
  offer: (body: {
    term: string;
    meaning: string;
    may_mean?: string;
    where_to_look?: string;
    area?: string;
    sources: Src[];
    credit: string;
  }) => request<{ id: string; status: string; note: string }>("POST", "/api/v1/explanations", body),
};
