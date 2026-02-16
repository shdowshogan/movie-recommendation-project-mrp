"use client";

import { useEffect, useMemo, useState } from "react";

type SearchResult = {
  tmdb_id: number;
  title: string;
  year?: string | null;
  poster_url?: string | null;
};

type HybridRec = {
  movie_id: string;
  cf_score: number;
  hybrid_score?: number | null;
  title?: string | null;
  poster_url?: string | null;
};

type SeedRec = {
  movie_id: string;
  content_score: number;
  cf_score?: number | null;
  hybrid_score?: number | null;
  title?: string | null;
  poster_url?: string | null;
};

type AuthUser = {
  id: number;
  email: string;
};

const heroPicks = [
  "The Matrix (1999)",
  "Inception (2010)",
  "Whiplash (2014)",
  "Blade Runner 2049 (2017)",
  "Parasite (2019)",
  "Se7en (1995)",
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

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export default function Home() {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [userId, setUserId] = useState("45");
  const [hybridLoading, setHybridLoading] = useState(false);
  const [hybridResults, setHybridResults] = useState<HybridRec[]>([]);
  const [hybridError, setHybridError] = useState<string | null>(null);

  const [seedLoading, setSeedLoading] = useState(false);
  const [seedResults, setSeedResults] = useState<SeedRec[]>([]);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [seedMode, setSeedMode] = useState<"hybrid" | "content">("hybrid");

  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordTips, setShowPasswordTips] = useState(false);

  const passwordTooShort = authPassword.length > 0 && authPassword.length < 8;

  const selectedIds = useMemo(
    () => new Set(selected.map((item) => item.tmdb_id)),
    [selected]
  );

  const handleSearch = async () => {
    if (query.trim().length < 2) {
      setSearchError("Type at least 2 characters.");
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    try {
      const resp = await fetch(
        `${API_BASE}/tmdb/search?query=${encodeURIComponent(query)}`
      );
      if (!resp.ok) {
        throw new Error("Search failed.");
      }
      const data = (await resp.json()) as SearchResult[];
      setSearchResults(data);
    } catch (err) {
      setSearchError("Search API unavailable. Start the server.");
    } finally {
      setSearchLoading(false);
    }
  };

  useEffect(() => {
    if (query.trim().length < 2) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }

    const timer = setTimeout(() => {
      handleSearch();
    }, 50);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (showPasswordTips && !passwordTooShort) {
      setShowPasswordTips(false);
    }
  }, [passwordTooShort, showPasswordTips]);

  useEffect(() => {
    const loadMe = async () => {
      try {
        const resp = await fetch(`${API_BASE}/auth/me`, {
          credentials: "include",
        });
        if (!resp.ok) return;
        const data = (await resp.json()) as { user: AuthUser };
        setAuthUser(data.user);
      } catch (err) {
        setAuthUser(null);
      }
    };
    loadMe();
  }, []);

  const addPick = (item: SearchResult) => {
    if (selectedIds.has(item.tmdb_id)) return;
    if (selected.length >= 10) return;
    setSelected((prev) => [...prev, item]);
  };

  const removePick = (tmdbId: number) => {
    setSelected((prev) => prev.filter((item) => item.tmdb_id !== tmdbId));
  };

  const loadHybrid = async () => {
    if (!userId.trim()) {
      setHybridError("Enter a user id.");
      return;
    }
    setHybridLoading(true);
    setHybridError(null);
    try {
      const resp = await fetch(
        `${API_BASE}/recommendations/hybrid/${userId}?n=10&include_titles=true`
      );
      if (!resp.ok) {
        throw new Error("Hybrid API failed.");
      }
      const data = (await resp.json()) as { results: HybridRec[] };
      setHybridResults(data.results || []);
    } catch (err) {
      setHybridError("Hybrid API unavailable. Start the server.");
    } finally {
      setHybridLoading(false);
    }
  };

  const generateFromSeeds = async () => {
    if (selected.length < 3) {
      setSeedError("Pick at least 3 movies.");
      return;
    }
    setSeedLoading(true);
    setSeedError(null);
    try {
      const endpoint =
        seedMode === "hybrid"
          ? `${API_BASE}/recommendations/seed-hybrid`
          : `${API_BASE}/recommendations/seed`;
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tmdb_ids: selected.map((item) => item.tmdb_id),
          n: 10,
        }),
      });
      if (!resp.ok) {
        throw new Error("Seed API failed.");
      }
      const data = (await resp.json()) as { results: SeedRec[] };
      setSeedResults(data.results || []);
    } catch (err) {
      setSeedError("Seed recommendations unavailable. Start the server.");
    } finally {
      setSeedLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!authEmail || !authPassword) {
      setAuthError("Enter email and password.");
      if (!authPassword) {
        setShowPasswordTips(true);
      }
      return;
    }
    if (passwordTooShort) {
      setAuthError("Password must be at least 8 characters.");
      setShowPasswordTips(true);
      return;
    }
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      if (!resp.ok) {
        if (resp.status === 422) {
          setShowPasswordTips(true);
        }
        throw new Error("Register failed");
      }
      const data = (await resp.json()) as { user: AuthUser };
      setAuthUser(data.user);
      setShowPasswordTips(false);
    } catch (err) {
      setAuthError("Registration failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!authEmail || !authPassword) {
      setAuthError("Enter email and password.");
      return;
    }
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      if (!resp.ok) {
        throw new Error("Login failed");
      }
      const data = (await resp.json()) as { user: AuthUser };
      setAuthUser(data.user);
    } catch (err) {
      setAuthError("Login failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
      setAuthUser(null);
    } catch (err) {
      setAuthError("Logout failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#1a1a25_0%,_#0b0b0f_45%,_#050507_100%)] text-[color:var(--foreground)]">
      <header className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center px-6 pt-8 md:grid-cols-3">
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
        <nav className="hidden items-center justify-center gap-6 text-sm text-[color:var(--muted)] md:flex">
          <span className="cursor-pointer">Discover</span>
          <span className="cursor-pointer">My Space</span>
        </nav>
        <div className="hidden md:block" />
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-10 px-6 pb-24 pt-12 lg:grid-cols-[320px_1fr]">
        <aside className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-black/40 p-5">
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                Account
              </p>
              <h2 className="text-lg font-semibold">
                {authUser ? "Signed in" : "Sign in"}
              </h2>
            </div>
            {authUser ? (
              <div className="space-y-3">
                <div className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-xs text-[color:var(--muted)]">
                  {authUser.email}
                </div>
                <button
                  onClick={handleLogout}
                  disabled={authLoading}
                  className="w-full cursor-pointer rounded-2xl border border-white/10 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)]"
                >
                  {authLoading ? "Signing out..." : "Sign out"}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  placeholder="Email"
                  value={authEmail}
                  onChange={(event) => setAuthEmail(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
                />
                <input
                  placeholder="Password"
                  type={showPassword ? "text" : "password"}
                  value={authPassword}
                  onChange={(event) => setAuthPassword(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="-mt-1 w-fit cursor-pointer text-[10px] uppercase tracking-[0.2em] text-[color:var(--muted)]"
                >
                  {showPassword ? "Hide password" : "See password"}
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleLogin}
                    disabled={authLoading}
                    className="cursor-pointer rounded-2xl border border-white/10 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)]"
                  >
                    {authLoading ? "Working..." : "Login"}
                  </button>
                  <button
                    onClick={handleRegister}
                    disabled={authLoading}
                    className="cursor-pointer rounded-2xl bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-black"
                  >
                    Register
                  </button>
                </div>
              </div>
            )}
            {authError ? (
              <p className="text-xs text-[#ffb4a2]">{authError}</p>
            ) : null}
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                Search
              </p>
              <h2 className="text-lg font-semibold">Find your picks</h2>
            </div>
            <input
              placeholder="Search films, directors, vibes"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
            />
            {showPasswordTips && passwordTooShort ? (
              <p className="text-xs text-[#ff8a8a]">
                Password tip: use at least 8 characters.
              </p>
            ) : null}
            <button
              onClick={handleSearch}
              className="w-full cursor-pointer rounded-2xl bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-black transition hover:brightness-110"
            >
              {searchLoading ? "Searching..." : "Search"}
            </button>
            {searchError ? (
              <p className="text-xs text-[#ffb4a2]">{searchError}</p>
            ) : null}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-[color:var(--muted)]">
              <span className="uppercase tracking-[0.3em]">Results</span>
              <span>{searchResults.length}</span>
            </div>
            <div className="grid gap-3">
              {searchResults.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-[color:var(--muted)]">
                  Search to see results.
                </div>
              ) : (
                searchResults.map((item) => (
                  <div
                    key={item.tmdb_id}
                    className="flex items-start gap-3 rounded-2xl border border-white/10 bg-black/30 p-3"
                  >
                    <div className="h-14 w-10 overflow-hidden rounded-lg bg-gradient-to-br from-[#2a2131] via-[#1c1c2a] to-[#0d0d12]">
                      {item.poster_url ? (
                        <img
                          src={item.poster_url}
                          alt={item.title}
                          className="h-full w-full object-cover"
                        />
                      ) : null}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-[color:var(--foreground)]">
                        {item.title}
                      </p>
                      <p className="text-xs text-[color:var(--muted)]">
                        {item.year || "Unknown year"}
                      </p>
                    </div>
                    <button
                      onClick={() => addPick(item)}
                      disabled={selectedIds.has(item.tmdb_id) || selected.length >= 10}
                      className="cursor-pointer rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[color:var(--foreground)] disabled:opacity-40"
                    >
                      {selectedIds.has(item.tmdb_id) ? "Added" : "Add"}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-[color:var(--muted)]">
              <span className="uppercase tracking-[0.3em]">Pick Tray</span>
              <span>{selected.length}/10</span>
            </div>
            {selected.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-[color:var(--muted)]">
                Add 5-10 films to shape your taste.
              </div>
            ) : (
              <div className="grid gap-3">
                {selected.map((item) => (
                  <div
                    key={item.tmdb_id}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/30 p-3"
                  >
                    <p className="text-sm font-semibold text-[color:var(--foreground)]">
                      {item.title}
                    </p>
                    <button
                      onClick={() => removePick(item.tmdb_id)}
                      className="cursor-pointer rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[color:var(--muted)]"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  onClick={generateFromSeeds}
                  className="cursor-pointer rounded-2xl bg-[color:var(--accent)] px-3 py-2 text-xs font-semibold text-black"
                >
                  {seedLoading ? "Generating..." : "Generate"}
                </button>
                {seedError ? (
                  <p className="text-xs text-[#ffb4a2]">{seedError}</p>
                ) : null}
              </div>
            )}
          </div>
        </aside>

        <div className="flex flex-col gap-14">
          <section className="grid gap-10">
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
            <div className="mt-2 flex flex-wrap gap-2">
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

          </section>

          <section className="grid gap-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                Because you like
              </p>
              <h3 className="text-xl font-semibold">Hybrid Intelligence</h3>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <input
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                placeholder="User id"
                className="rounded-full border border-white/10 bg-black/30 px-4 py-2 text-xs text-[color:var(--foreground)]"
              />
              <button
                onClick={loadHybrid}
                className="cursor-pointer rounded-full bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-black"
              >
                {hybridLoading ? "Loading" : "Load"}
              </button>
            </div>
          </div>
          {hybridError ? (
            <p className="text-xs text-[#ffb4a2]">{hybridError}</p>
          ) : null}
          <div className="grid gap-4 md:grid-cols-5">
            {hybridResults.length === 0
              ? Array.from({ length: 5 }).map((_, idx) => (
                  <div
                    key={`row-${idx}`}
                    className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">Recommendation {idx + 1}</p>
                      <p className="text-xs text-[color:var(--muted)]">Hybrid match --</p>
                    </div>
                  </div>
                ))
              : hybridResults.map((item) => (
                  <div
                    key={item.movie_id}
                    className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="aspect-[2/3] overflow-hidden rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]">
                      {item.poster_url ? (
                        <img
                          src={item.poster_url}
                          alt={item.title || "Recommendation"}
                          className="h-full w-full object-cover"
                          loading="lazy"
                          decoding="async"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-black/40 text-[10px] uppercase tracking-[0.3em] text-[color:var(--muted)]">
                          No poster
                        </div>
                      )}
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">
                        {item.title || `Movie ${item.movie_id}`}
                      </p>
                      <p className="text-xs text-[color:var(--muted)]">
                        Hybrid {item.hybrid_score?.toFixed(3) ?? "--"}
                      </p>
                    </div>
                  </div>
                ))}
          </div>
          </section>

          <section className="grid gap-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--muted)]">
                  Seed Picks
                </p>
                <h3 className="text-xl font-semibold">Taste-Based Results</h3>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-[10px] uppercase tracking-[0.2em]">
                <button
                  onClick={() => setSeedMode("hybrid")}
                  disabled={seedLoading}
                  className={`cursor-pointer rounded-full px-3 py-1 ${
                    seedMode === "hybrid"
                      ? "bg-[color:var(--accent)] text-black"
                      : "text-[color:var(--muted)]"
                  }`}
                >
                  Hybrid
                </button>
                <button
                  onClick={() => setSeedMode("content")}
                  disabled={seedLoading}
                  className={`cursor-pointer rounded-full px-3 py-1 ${
                    seedMode === "content"
                      ? "bg-[color:var(--accent)] text-black"
                      : "text-[color:var(--muted)]"
                  }`}
                >
                  Content
                </button>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-5">
              {seedResults.length === 0
                ? Array.from({ length: 5 }).map((_, idx) => (
                    <div
                      key={`seed-${idx}`}
                      className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                    >
                      <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">Seed Rec {idx + 1}</p>
                        <p className="text-xs text-[color:var(--muted)]">Content match --</p>
                      </div>
                    </div>
                  ))
                : seedResults.map((item) => (
                    <div
                      key={item.movie_id}
                      className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                    >
                      <div className="aspect-[2/3] overflow-hidden rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]">
                        {item.poster_url ? (
                          <img
                            src={item.poster_url}
                            alt={item.title || "Seed recommendation"}
                            className="h-full w-full object-cover"
                            loading="lazy"
                            decoding="async"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center bg-black/40 text-[10px] uppercase tracking-[0.3em] text-[color:var(--muted)]">
                            No poster
                          </div>
                        )}
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">
                          {item.title || `Movie ${item.movie_id}`}
                        </p>
                        <p className="text-xs text-[color:var(--muted)]">
                          {seedMode === "hybrid"
                            ? `Hybrid ${item.hybrid_score?.toFixed(3) ?? "--"}`
                            : `Content ${item.content_score.toFixed(3)}`}
                        </p>
                      </div>
                    </div>
                  ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
