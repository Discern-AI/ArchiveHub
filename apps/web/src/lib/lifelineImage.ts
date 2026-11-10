/**
 * The Lifeline as a picture to share or print as a poster. Living relatives are left out
 * (their dates are private anyway) and a note says how many, so nothing shared shows them.
 */
import { spans, statusAt, lifeLabel, type LifePerson, type Overlay } from "./lifeline";

const KIND_COLOUR: Record<string, string> = {
  war: "#b3261e",
  records: "#1f5c4d",
  law: "#6b5a3e",
  calendar: "#52635e",
  local: "#a14a12",
  custom: "#6b3fa0",
};

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

export interface ImageOptions {
  title: string;
  people: LifePerson[];
  overlays: Overlay[];
  lo: number;
  hi: number;
  year: number;
}

export function lifelineSvg({ title, people, overlays, lo, hi, year }: ImageOptions): string {
  const shown = people.filter((p) => !p.living);
  const hidden = people.length - shown.length;
  const W = 1600;
  const NAME = 260;
  const ROW = 26;
  const TOP = 110;
  const plot = W - NAME - 40;
  const x = (y: number) => NAME + ((y - lo) / Math.max(1, hi - lo)) * plot;
  const H = TOP + shown.length * ROW + 90;
  const parts: string[] = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="Segoe UI, Arial, sans-serif">`,
    `<rect width="${W}" height="${H}" fill="#ffffff"/>`,
    `<text x="24" y="44" font-size="30" font-weight="600" fill="#14322c">${esc(title)}</text>`,
    `<text x="24" y="74" font-size="16" fill="#52635e">Lifeline, ${lo}–${hi}. Faded ends: a date is approximate or not recorded.</text>`,
  );
  const step = hi - lo > 200 ? 50 : hi - lo > 80 ? 20 : 10;
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) {
    parts.push(
      `<line x1="${x(t)}" y1="${TOP - 6}" x2="${x(t)}" y2="${TOP + shown.length * ROW}" stroke="#e4eae6"/>`,
      `<text x="${x(t)}" y="${TOP - 12}" font-size="13" text-anchor="middle" fill="#52635e">${t}</text>`,
    );
  }
  for (const o of overlays) {
    const a = Math.max(lo, o.year_from);
    const b = Math.min(hi, (o.year_to ?? o.year_from) + (o.year_to ? 1 : 0));
    if (b < lo || a > hi) continue;
    const w = o.year_to ? Math.max(2, x(b) - x(a)) : 2;
    parts.push(
      `<rect x="${x(a)}" y="${TOP}" width="${w}" height="${shown.length * ROW}" fill="${KIND_COLOUR[o.kind] ?? "#52635e"}" opacity="${o.year_to ? 0.12 : 0.5}"><title>${esc(o.title)}</title></rect>`,
    );
  }
  shown.forEach((p, i) => {
    const y = TOP + i * ROW;
    const { possibleFrom, possibleTo, sureFrom, sureTo } = spans(p);
    parts.push(`<text x="24" y="${y + 17}" font-size="14" fill="#14322c">${esc(p.name)}</text>`);
    if (possibleFrom === null || possibleTo === null) {
      parts.push(
        `<text x="${NAME}" y="${y + 17}" font-size="12" fill="#52635e">No dates recorded</text>`,
      );
      return;
    }
    const from = sureFrom ?? sureTo ?? possibleFrom;
    const to = sureFrom !== null && sureTo !== null && sureFrom <= sureTo ? sureTo : from;
    const live = statusAt(p, year);
    const colour = live === "alive" || live === "uncertain" ? "#1f5c4d" : "#8a9c96";
    const id = `g${i}`;
    parts.push(
      `<defs><linearGradient id="${id}i"><stop offset="0" stop-color="${colour}" stop-opacity="0"/><stop offset="1" stop-color="${colour}" stop-opacity="0.9"/></linearGradient>` +
        `<linearGradient id="${id}o"><stop offset="0" stop-color="${colour}" stop-opacity="0.9"/><stop offset="1" stop-color="${colour}" stop-opacity="0"/></linearGradient></defs>`,
    );
    const fadeIn = Math.max(possibleFrom, from - 25);
    const fadeOut = Math.min(possibleTo, to + 25);
    if (!p.start || p.start.certainty !== "exact")
      parts.push(
        `<rect x="${x(fadeIn)}" y="${y + 6}" width="${Math.max(0, x(from) - x(fadeIn))}" height="14" fill="url(#${id}i)"/>`,
      );
    parts.push(
      `<rect x="${x(from)}" y="${y + 6}" width="${Math.max(2, x(to) - x(from))}" height="14" rx="3" fill="${colour}"><title>${esc(lifeLabel(p))}</title></rect>`,
    );
    if (!p.end || p.end.certainty !== "exact")
      parts.push(
        `<rect x="${x(to)}" y="${y + 6}" width="${Math.max(0, x(fadeOut) - x(to))}" height="14" fill="url(#${id}o)"/>`,
      );
  });
  parts.push(
    `<line x1="${x(year)}" y1="${TOP - 6}" x2="${x(year)}" y2="${TOP + shown.length * ROW}" stroke="#b86e12" stroke-width="2"/>`,
    `<text x="${x(year)}" y="${TOP + shown.length * ROW + 22}" font-size="14" text-anchor="middle" fill="#b86e12" font-weight="600">${year}</text>`,
  );
  const foot = [
    "Made with ArchiveHub from the family's own records.",
    hidden
      ? `${hidden} living ${hidden === 1 ? "relative is" : "relatives are"} left out to keep them private.`
      : "",
  ]
    .filter(Boolean)
    .join(" ");
  parts.push(
    `<text x="24" y="${H - 24}" font-size="13" fill="#52635e">${esc(foot)}</text>`,
    "</svg>",
  );
  return parts.join("");
}

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Download as PNG; if the browser can't draw it, as SVG instead. */
export async function downloadLifelineImage(opts: ImageOptions, filename: string): Promise<void> {
  const svg = lifelineSvg(opts);
  const svgBlob = new Blob([svg], { type: "image/svg+xml" });
  try {
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("image"));
      img.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas");
    ctx.drawImage(img, 0, 0);
    URL.revokeObjectURL(url);
    const png = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/png"));
    if (!png) throw new Error("png");
    save(png, `${filename}.png`);
  } catch {
    save(svgBlob, `${filename}.svg`);
  }
}
