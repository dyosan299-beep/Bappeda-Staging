export function KpiCard({ label, value, sub, icon: Icon, accent = "primary", testid }) {
  const accentClass = {
    primary: "text-primary",
    amber: "text-[hsl(32_90%_44%)]",
    indigo: "text-[hsl(243_55%_50%)]",
    fuchsia: "text-[hsl(292_84%_50%)]",
    emerald: "text-[hsl(160_84%_27%)]",
  }[accent];

  return (
    <div
      data-testid={testid}
      className="flex flex-col justify-between rounded-lg border-2 border-border bg-card p-6 transition-colors hover:border-accent"
    >
      <div className="flex items-start justify-between">
        <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        {Icon && <Icon className={`h-6 w-6 ${accentClass}`} />}
      </div>
      <p className={`mt-3 font-head text-3xl font-extrabold tabular-nums md:text-4xl ${accentClass}`}>
        {value}
      </p>
      {sub && <p className="mt-1 text-sm text-muted-foreground">{sub}</p>}
    </div>
  );
}
