export const STARTERS = [
  {
    title: "Record your family or local history",
    body: "Upload trees, diaries, letters, photos and videos, or just talk.",
    prompt: "I want to record my family's history. Where should I start?",
  },
  {
    title: "Research a person, place or event",
    body: "Find out what exists, where to look and what to do next.",
    prompt: "I want to research a person, place or event. How should I begin?",
  },
  {
    title: "Are you a historian, archivist or blogger?",
    body: "Store your work and publish it from a homepage, part-time or full-time.",
    prompt: "I'm a local historian and I'm looking for a home for my work.",
  },
  {
    title: "Is this for your business or services?",
    body: "Let people find you, tip you and book you for talks or research.",
    prompt: "I offer talks and research and want people to be able to find me.",
  },
];

export function StarterPrompts({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto my-auto flex w-full max-w-[760px] flex-col gap-5 py-8">
      <h1 className="m-0 font-serif text-[40px] leading-[1.15] font-semibold">
        What are you working on?
      </h1>
      <p className="m-0 text-muted">Pick one of these, or just start typing below.</p>
      <div className="flex flex-col border-t border-line">
        {STARTERS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => onPick(s.prompt)}
            className="min-h-16 cursor-pointer border-b border-line bg-transparent px-2 py-3 text-left hover:bg-tint"
          >
            <span className="block font-semibold">{s.title}</span>
            <span className="block text-muted">{s.body}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
