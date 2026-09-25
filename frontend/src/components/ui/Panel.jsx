// A rail section: hairline divider, small accent dot, optional right-aligned
// badge. Deliberately not a floating shadow-card - the rail reads as one
// continuous instrument panel, not a stack of separate widgets.
export default function Panel({ title, accent, badge, children }) {
  return (
    <section className="border-b border-[var(--color-border)] py-4 first:pt-0 last:border-b-0">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium flex items-center gap-2 text-[var(--color-text)]">
          {accent && (
            <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: accent }} />
          )}
          {title}
        </h2>
        {badge}
      </div>
      {children}
    </section>
  );
}
