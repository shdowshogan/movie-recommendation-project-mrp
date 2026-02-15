const heroPicks = [
  "The Matrix (1999)",
  "Inception (2010)",
  "Whiplash (2014)",
  "Blade Runner 2049 (2017)",
  "Parasite (2019)",
  "Se7en (1995)",
];

const spotlight = [
  { title: "Neon Noir", subtitle: "Brooding futures and sharp silhouettes" },
  { title: "Quiet Storm", subtitle: "Character-driven thrillers" },
  { title: "Midnight Myth", subtitle: "Dark fantasy and folklore" },
  { title: "Cosmic Drift", subtitle: "Headphones on, space out" },
];

const picks = [
  "Arrival",
  "The Social Network",
  "Ex Machina",
  "Her",
  "The Prestige",
  "The Grand Budapest Hotel",
  "Drive",
  "Prisoners",
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#1a1a25_0%,_#0b0b0f_45%,_#050507_100%)] text-[color:var(--foreground)]">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 pt-8">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-[conic-gradient(from_120deg,_#d7b36c,_#7dd3fc,_#d7b36c)]" />
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-[color:var(--muted)]">
              CineMind
            </p>
            <p className="text-lg font-semibold text-[color:var(--foreground)]">
              Signal Curator
            </p>
          </div>
        </div>
        <nav className="hidden items-center gap-6 text-sm text-[color:var(--muted)] md:flex">
          <span className="cursor-default">Discover</span>
          <span className="cursor-default">Moments</span>
          <span className="cursor-default">Taste DNA</span>
        </nav>
        <button className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-[color:var(--foreground)]">
          Join Beta
        </button>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-14 px-6 pb-24 pt-12">
        <section className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="flex flex-col gap-6">
            <p className="text-xs uppercase tracking-[0.4em] text-[color:var(--accent)]">
              Pick 5-10 films
            </p>
            <h1 className="font-[var(--font-display)] text-4xl leading-tight text-[color:var(--foreground)] sm:text-5xl">
              A cinematic brain that learns your taste in minutes.
            </h1>
            <p className="max-w-xl text-base leading-relaxed text-[color:var(--muted)]">
              Choose a handful of movies you love. CineMind builds a moodboard of your taste,
              blends it with collaborative signals, and returns what you should watch next.
            </p>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <div className="flex flex-col gap-4 sm:flex-row">
                <input
                  placeholder="Search films, directors, vibes"
                  className="flex-1 rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
                />
                <button className="rounded-2xl bg-[color:var(--accent)] px-5 py-3 text-sm font-semibold text-black">
                  Add Pick
                </button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {heroPicks.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[color:var(--foreground)]"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
              Taste Signal
            </p>
            <div className="space-y-4">
              {spotlight.map((item) => (
                <div key={item.title} className="rounded-2xl border border-white/10 bg-black/40 p-4">
                  <p className="text-sm font-semibold text-[color:var(--foreground)]">
                    {item.title}
                  </p>
                  <p className="text-xs text-[color:var(--muted)]">{item.subtitle}</p>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-white/10">
                    <div className="h-1.5 w-2/3 rounded-full bg-[color:var(--accent-2)]" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 rounded-3xl border border-white/10 bg-[color:var(--surface)] p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                Your Pick Tray
              </p>
              <h2 className="text-xl font-semibold">Selected Films</h2>
            </div>
            <button className="rounded-full border border-white/10 px-4 py-2 text-xs uppercase tracking-[0.2em]">
              Generate
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {picks.map((title) => (
              <div
                key={title}
                className="group flex flex-col gap-4 rounded-2xl border border-white/10 bg-black/30 p-4"
              >
                <div className="aspect-[3/4] w-full rounded-2xl bg-gradient-to-br from-[#3b1c32] via-[#1b1b2f] to-[#0a0a0f]" />
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-[color:var(--foreground)]">
                    {title}
                  </p>
                  <button className="rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[color:var(--muted)]">
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                Because you like
              </p>
              <h3 className="text-xl font-semibold">Dark Intelligence</h3>
            </div>
            <button className="text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
              Refresh
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-5">
            {Array.from({ length: 5 }).map((_, idx) => (
              <div
                key={`row-${idx}`}
                className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
              >
                <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold">Recommendation {idx + 1}</p>
                  <p className="text-xs text-[color:var(--muted)]">Hybrid match 0.{8 + idx}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
