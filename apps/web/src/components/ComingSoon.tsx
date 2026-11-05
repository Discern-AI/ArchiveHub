export function ComingSoon({ title, pkg }: { title: string; pkg?: string }) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-12">
      <h1 className="m-0 font-serif text-[34px] font-semibold">{title}</h1>
      {pkg && (
        <p className="mt-2 text-muted">
          This part of ArchiveHub arrives in {pkg}. You can still start a chat from the left.
        </p>
      )}
    </div>
  );
}
