/**
 * Records that could be ordered for a person, each with who holds it, what it should
 * show, every fee, how long it takes and its rights. ArchiveHub doesn't sell them yet:
 * you order from the holder, and the order is tracked here until the record arrives.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, archiveApi } from "../../lib/api";
import {
  lineageApi,
  pounds,
  type Offer,
  type OfferEvent,
  type RecordOrder,
} from "../../lib/lineages";

export function OrderRecords({ projectId, personId }: { projectId: string; personId: string }) {
  const offers = useQuery({
    queryKey: ["record-offers", projectId, personId],
    queryFn: () => lineageApi.offers(projectId, personId),
  });
  const orders = useQuery({
    queryKey: ["record-orders", projectId],
    queryFn: () => lineageApi.orders(projectId),
  });
  const mine = (orders.data ?? []).filter((o) => o.person_id === personId);
  return (
    <section aria-label="Order records" className="flex flex-col gap-3">
      <p className="m-0 text-sm text-muted">{offers.data?.note}</p>
      {mine.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="m-0 text-base font-semibold">Your orders</h3>
          {mine.map((o) => (
            <OrderCard key={o.id} order={o} projectId={projectId} />
          ))}
        </div>
      )}
      {offers.data?.events.length === 0 && (
        <p className="m-0">No dated events to order records for yet.</p>
      )}
      {offers.data?.events.map((e, i) => (
        <EventOffers key={`${e.event}-${i}`} e={e} projectId={projectId} personId={personId} />
      ))}
    </section>
  );
}

function EventOffers({
  e,
  projectId,
  personId,
}: {
  e: OfferEvent;
  projectId: string;
  personId: string;
}) {
  const label = `${e.event[0].toUpperCase()}${e.event.slice(1)}${e.with ? ` to ${e.with}` : ""}`;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="m-0 text-base font-semibold">
        {label}
        <span className="font-normal text-muted">
          {" "}
          {[e.date_text, e.place].filter(Boolean).join(", ")}
        </span>
      </h3>
      {e.note && <p className="m-0 text-sm">{e.note}</p>}
      {e.offers.map((o) => (
        <OfferCard
          key={o.key}
          offer={o}
          event={e.event}
          projectId={projectId}
          personId={personId}
        />
      ))}
    </div>
  );
}

function OfferCard({
  offer,
  event,
  projectId,
  personId,
}: {
  offer: Offer;
  event: string;
  projectId: string;
  personId: string;
}) {
  const qc = useQueryClient();
  const [ref, setRef] = useState("");
  const plan = useMutation({
    mutationFn: () =>
      lineageApi.plan({
        project_id: projectId,
        person_id: personId,
        offer_key: offer.key,
        event,
        index_reference: ref,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["record-orders", projectId] }),
  });
  return (
    <div
      role="group"
      aria-label={`${offer.title} of the ${event}`}
      className="flex flex-col gap-1 rounded-lg border border-line bg-surface p-3 text-sm"
    >
      <strong>
        {offer.title} · {pounds(offer.total_pence)}
      </strong>
      <span>{offer.should_show}</span>
      <span className="text-muted">
        Held by {offer.holder}. {offer.delivery}
      </span>
      <ul className="m-0 pl-5">
        {offer.fees.map((f) => (
          <li key={f.label}>
            {f.label}: {pounds(f.pence)}
          </li>
        ))}
        <li>ArchiveHub fee: none</li>
      </ul>
      <span className="text-muted">{offer.rights_label}</span>
      <span className="text-xs text-muted">
        Prices from{" "}
        {offer.sources.map((s, i) => (
          <span key={s.url}>
            {i > 0 && " and "}
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
            </a>
          </span>
        ))}
        , checked {offer.checked_on}.
      </span>
      {offer.needs_index_reference && (
        <label className="flex flex-col gap-1 font-medium">
          GRO index reference
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            className="min-h-11 rounded-lg border border-control px-3 font-normal"
          />
        </label>
      )}
      <span className="flex flex-wrap gap-2">
        <a
          href={offer.url}
          target="_blank"
          rel="noreferrer"
          className="flex min-h-11 items-center rounded-lg border border-accent px-3 font-medium no-underline"
        >
          Order from the holder ↗
        </a>
        <button
          type="button"
          onClick={() => plan.mutate()}
          disabled={plan.isPending || plan.isSuccess}
          className="min-h-11 cursor-pointer rounded-lg bg-accent px-3 font-semibold text-white"
        >
          {plan.isSuccess ? "Being tracked" : "Track this order"}
        </button>
      </span>
      <span className="text-xs text-muted">{offer.how}</span>
      {plan.isError && (
        <p className="m-0 text-warning">
          {plan.error instanceof ApiError ? plan.error.message : "It couldn't be tracked."}
        </p>
      )}
    </div>
  );
}

function OrderCard({ order, projectId }: { order: RecordOrder; projectId: string }) {
  const qc = useQueryClient();
  const [ref, setRef] = useState(order.reference);
  const [fileId, setFileId] = useState("");
  const files = useQuery({
    queryKey: ["files", projectId, "all"],
    queryFn: () => archiveApi.files(projectId),
    enabled: order.status === "ordered",
  });
  const update = useMutation({
    mutationFn: (body: { status?: string; reference?: string; file_id?: string }) =>
      lineageApi.update(order.id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["record-orders", projectId] }),
  });
  return (
    <div
      role="group"
      aria-label={order.title}
      className="flex flex-col gap-1 rounded-lg border border-line p-3 text-sm"
    >
      <strong>{order.title}</strong>
      <span>
        {order.status_label} · {pounds(order.total_pence)} · {order.route_label}
      </span>
      {order.details.index_reference && (
        <span className="text-muted">Index reference: {order.details.index_reference}</span>
      )}
      {order.status === "planned" && (
        <span className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1">
            Their order reference (optional)
            <input
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              className="min-h-11 rounded-lg border border-control px-3"
            />
          </label>
          <button
            type="button"
            onClick={() => update.mutate({ status: "ordered", reference: ref })}
            className="min-h-11 cursor-pointer rounded-lg bg-accent px-3 font-semibold text-white"
          >
            I&apos;ve ordered it
          </button>
          <button
            type="button"
            onClick={() => update.mutate({ status: "cancelled" })}
            className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
          >
            Cancel
          </button>
        </span>
      )}
      {order.status === "ordered" && (
        <span className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1">
            The copy, uploaded to your Archive
            <select
              value={fileId}
              onChange={(e) => setFileId(e.target.value)}
              className="min-h-11 rounded-lg border border-control bg-surface px-2"
            >
              <option value="">Choose a file</option>
              {(files.data ?? []).map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={!fileId}
            onClick={() => update.mutate({ status: "received", file_id: fileId })}
            className="min-h-11 cursor-pointer rounded-lg bg-accent px-3 font-semibold text-white"
          >
            It&apos;s arrived
          </button>
        </span>
      )}
      {order.status === "received" && order.file_id && <span>Filed in your Archive.</span>}
      {update.isError && (
        <p className="m-0 text-warning">
          {update.error instanceof ApiError ? update.error.message : "That couldn't be saved."}
        </p>
      )}
    </div>
  );
}
