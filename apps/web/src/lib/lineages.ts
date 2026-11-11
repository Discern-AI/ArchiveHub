/** Lineages and record orders. */
import { request } from "./api";

export interface LineageSubject {
  type: string;
  id: string;
  name: string;
  kind: string;
  roles: { role: string; label: string; count: number }[];
}

export interface Holder {
  id: string;
  name: string | null;
  hidden: boolean;
  year_from: number | null;
  year_to: number | null;
  date_text: string;
  status: string;
  sources: { title: string; url: string; source: string; what_it_says: string }[];
  connections: {
    project: string;
    project_id: string;
    person_id: string;
    name: string;
    reason: string;
  }[];
}

export interface Lineage {
  subject: { id: string; name: string; type: string };
  role: string;
  role_label: string;
  roles: LineageSubject["roles"];
  holders: Holder[];
  gaps: { from: number; to: number }[];
  hidden_recent: number;
  notes: string[];
}

export interface Offer {
  key: string;
  title: string;
  holder: string;
  route: string;
  fees: { label: string; pence: number }[];
  total_pence: number;
  delivery: string;
  should_show: string;
  needs_index_reference: boolean;
  url: string;
  how: string;
  rights_label: string;
  sources: { title: string; url: string }[];
  checked_on: string;
}

export interface OfferEvent {
  event: "birth" | "marriage" | "death";
  year: number | null;
  date_text: string;
  place: string;
  with?: string;
  offers: Offer[];
  note: string;
}

export interface RecordOrder {
  id: string;
  title: string;
  holder: string;
  route_label: string;
  fees: { label: string; pence: number }[];
  total_pence: number;
  delivery: string;
  url: string;
  rights_label: string;
  details: { event?: string; index_reference?: string };
  status: "planned" | "ordered" | "received" | "cancelled";
  status_label: string;
  reference: string;
  file_id: string | null;
  person_id: string | null;
}

export const pounds = (p: number) => `£${(p / 100).toFixed(2)}`;

export const lineageApi = {
  subjects: () => request<LineageSubject[]>("GET", "/api/v1/lineages"),
  lineage: (type: string, id: string, role = "") =>
    request<Lineage>("GET", `/api/v1/lineages/${type}/${id}${role ? `?role=${role}` : ""}`),
  offers: (projectId: string, personId: string) =>
    request<{ events: OfferEvent[]; note: string }>(
      "GET",
      `/api/v1/projects/${projectId}/people/${personId}/record-offers`,
    ),
  orders: (projectId: string) =>
    request<RecordOrder[]>("GET", `/api/v1/record-orders?project_id=${projectId}`),
  plan: (body: {
    project_id: string;
    person_id: string;
    offer_key: string;
    event: string;
    index_reference?: string;
  }) => request<RecordOrder>("POST", "/api/v1/record-orders", body),
  update: (
    id: string,
    body: { status?: string; reference?: string; file_id?: string; note?: string },
  ) => request<RecordOrder>("PATCH", `/api/v1/record-orders/${id}`, body),
};
