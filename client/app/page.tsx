"use client";

import { useEffect, useMemo, useRef, useState } from "react";

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

type UserLikedMovie = {
  movie_id: string;
  rating: number;
  title?: string | null;
  poster_url?: string | null;
};

type DiscoverItem = {
  tmdb_id: number;
  title: string;
  year?: string | null;
  poster_url?: string | null;
  overview?: string | null;
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
const USER_ID_MAX = 138493;

export default function Home() {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"discover" | "my-space">("discover");
  const [discoverMode, setDiscoverMode] = useState<
    "trending" | "upcoming" | "filtered"
  >("trending");
  const [discoverItems, setDiscoverItems] = useState<DiscoverItem[]>([]);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverError, setDiscoverError] = useState<string | null>(null);
  const [likedIds, setLikedIds] = useState<Record<number, boolean>>({});
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [discoverGenres, setDiscoverGenres] = useState<{ id: number; name: string }[]>(
    []
  );
  const [discoverYearFrom, setDiscoverYearFrom] = useState("");
  const [discoverYearTo, setDiscoverYearTo] = useState("");
  const [discoverRuntimeMin, setDiscoverRuntimeMin] = useState("");
  const [discoverRuntimeMax, setDiscoverRuntimeMax] = useState("");
  const [discoverGenreIds, setDiscoverGenreIds] = useState<number[]>([]);
  const [discoverCast, setDiscoverCast] = useState("");
  const [discoverDirector, setDiscoverDirector] = useState("");

  const [userId, setUserId] = useState("45");
  const [hybridLoading, setHybridLoading] = useState(false);
  const [hybridResults, setHybridResults] = useState<HybridRec[]>([]);
  const [hybridError, setHybridError] = useState<string | null>(null);
  const [hybridYearFrom, setHybridYearFrom] = useState("");
  const [hybridYearTo, setHybridYearTo] = useState("");
  const [likedLoading, setLikedLoading] = useState(false);
  const [likedMovies, setLikedMovies] = useState<UserLikedMovie[]>([]);
  const [likedError, setLikedError] = useState<string | null>(null);

  const [seedLoading, setSeedLoading] = useState(false);
  const [seedResults, setSeedResults] = useState<SeedRec[]>([]);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [seedMode, setSeedMode] = useState<"hybrid" | "content">("hybrid");
  const [seedGenerated, setSeedGenerated] = useState(false);
  const [seedYearFrom, setSeedYearFrom] = useState("");
  const [seedYearTo, setSeedYearTo] = useState("");

  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordTips, setShowPasswordTips] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const profileRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    if (activeTab !== "discover") return;
    if (discoverGenres.length > 0) return;
    const loadGenres = async () => {
      try {
        const resp = await fetch(`${API_BASE}/tmdb/genres`);
        if (!resp.ok) return;
        const data = (await resp.json()) as { id: number; name: string }[];
        setDiscoverGenres(data);
      } catch (err) {
        setDiscoverGenres([]);
      }
    };
    loadGenres();
  }, [activeTab, discoverGenres.length]);

  useEffect(() => {
    if (activeTab !== "discover") return;
    const loadDiscover = async () => {
      setDiscoverLoading(true);
      setDiscoverError(null);
      try {
        let endpoint = "";
        if (discoverMode === "filtered") {
          const params = new URLSearchParams();
          params.set("limit", "12");
          if (discoverYearFrom.trim()) {
            params.set("year_from", discoverYearFrom.trim());
          }
          if (discoverYearTo.trim()) {
            params.set("year_to", discoverYearTo.trim());
          }
          if (discoverRuntimeMin.trim()) {
            params.set("runtime_min", discoverRuntimeMin.trim());
          }
          if (discoverRuntimeMax.trim()) {
            params.set("runtime_max", discoverRuntimeMax.trim());
          }
          if (discoverGenreIds.length > 0) {
            params.set("genre_ids", discoverGenreIds.join(","));
          }
          if (discoverCast.trim()) {
            params.set("cast", discoverCast.trim());
          }
          if (discoverDirector.trim()) {
            params.set("director", discoverDirector.trim());
          }
          endpoint = `${API_BASE}/tmdb/discover?${params.toString()}`;
        } else {
          endpoint =
            discoverMode === "trending"
              ? `${API_BASE}/tmdb/trending?limit=12`
              : `${API_BASE}/tmdb/upcoming?limit=12`;
        }
        const resp = await fetch(endpoint);
        if (!resp.ok) {
          throw new Error("Discover API failed.");
        }
        const data = (await resp.json()) as DiscoverItem[];
        setDiscoverItems(data);
      } catch (err) {
        setDiscoverError("Discover feed unavailable. Start the server.");
      } finally {
        setDiscoverLoading(false);
      }
    };
    loadDiscover();
  }, [
    activeTab,
    discoverMode,
    discoverYearFrom,
    discoverYearTo,
    discoverRuntimeMin,
    discoverRuntimeMax,
    discoverGenreIds,
    discoverCast,
    discoverDirector,
  ]);

  useEffect(() => {
    if (!profileOpen) return;
    const handleOutside = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (profileRef.current && target && !profileRef.current.contains(target)) {
        setProfileOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("touchstart", handleOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("touchstart", handleOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [profileOpen]);

  const addPick = (item: SearchResult) => {
    if (selectedIds.has(item.tmdb_id)) return;
    if (selected.length >= 10) return;
    setSelected((prev) => [...prev, item]);
  };

  const removePick = (tmdbId: number) => {
    setSelected((prev) => prev.filter((item) => item.tmdb_id !== tmdbId));
  };

  const toggleLike = (tmdbId: number) => {
    setLikedIds((prev) => ({ ...prev, [tmdbId]: !prev[tmdbId] }));
  };

  const setRating = (tmdbId: number, value: number) => {
    setRatings((prev) => ({ ...prev, [tmdbId]: value }));
  };

  const toggleDiscoverGenre = (genreId: number) => {
    setDiscoverGenreIds((prev) =>
      prev.includes(genreId)
        ? prev.filter((id) => id !== genreId)
        : [...prev, genreId]
    );
  };

  const applyDiscoverFilters = () => {
    setDiscoverMode("filtered");
  };

  const resetDiscoverFilters = () => {
    setDiscoverYearFrom("");
    setDiscoverYearTo("");
    setDiscoverRuntimeMin("");
    setDiscoverRuntimeMax("");
    setDiscoverGenreIds([]);
    setDiscoverCast("");
    setDiscoverDirector("");
    setDiscoverMode("trending");
  };

  const loadHybrid = async (targetUserId?: string) => {
    const resolvedUserId = (targetUserId ?? userId).trim();
    if (!resolvedUserId) {
      setHybridError("Enter a user id.");
      return;
    }
    setHybridLoading(true);
    setHybridError(null);
    try {
      const params = new URLSearchParams({ n: "10", include_titles: "true" });
      if (hybridYearFrom.trim()) {
        params.set("year_from", hybridYearFrom.trim());
      }
      if (hybridYearTo.trim()) {
        params.set("year_to", hybridYearTo.trim());
      }
      const resp = await fetch(
        `${API_BASE}/recommendations/hybrid/${resolvedUserId}?${params.toString()}`
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

  const loadUserLikes = async (targetUserId?: string) => {
    const resolvedUserId = (targetUserId ?? userId).trim();
    if (!resolvedUserId) return;
    setLikedLoading(true);
    setLikedError(null);
    try {
      const resp = await fetch(
        `${API_BASE}/users/${resolvedUserId}/ratings?limit=6&min_rating=4`
      );
      if (!resp.ok) {
        throw new Error("Liked movies API failed.");
      }
      const data = (await resp.json()) as UserLikedMovie[];
      setLikedMovies(data);
    } catch (err) {
      setLikedError("User likes unavailable.");
      setLikedMovies([]);
    } finally {
      setLikedLoading(false);
    }
  };

  const refreshHybrid = async (targetUserId?: string) => {
    const resolvedUserId = targetUserId ?? userId;
    setHybridResults([]);
    setLikedMovies([]);
    await Promise.all([loadHybrid(resolvedUserId), loadUserLikes(resolvedUserId)]);
  };

  const randomizeUser = () => {
    const nextId = String(Math.floor(Math.random() * USER_ID_MAX) + 1);
    setUserId(nextId);
    refreshHybrid(nextId);
  };

  const generateFromSeeds = async (modeOverride?: "content" | "hybrid") => {
    const resolvedMode = modeOverride ?? seedMode;
    if (modeOverride && seedMode !== modeOverride) {
      setSeedMode(modeOverride);
    }
    if (selected.length < 3) {
      setSeedError("Pick at least 3 movies.");
      return;
    }
    setSeedLoading(true);
    setSeedError(null);
    try {
      const endpointBase =
        resolvedMode === "hybrid"
          ? `${API_BASE}/recommendations/seed-hybrid`
          : `${API_BASE}/recommendations/seed`;
      const params = new URLSearchParams();
      if (seedYearFrom.trim()) {
        params.set("year_from", seedYearFrom.trim());
      }
      if (seedYearTo.trim()) {
        params.set("year_to", seedYearTo.trim());
      }
      const endpoint = params.toString()
        ? `${endpointBase}?${params.toString()}`
        : endpointBase;
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
      setSeedGenerated(true);
      if (activeTab === "discover") {
        setActiveTab("my-space");
      }
    } catch (err) {
      setSeedError("Seed recommendations unavailable. Start the server.");
    } finally {
      setSeedLoading(false);
    }
  };

  useEffect(() => {
    if (!seedGenerated) return;
    if (seedLoading) return;
    if (selected.length < 3) return;
    setSeedResults([]);
    generateFromSeeds();
  }, [seedMode]);

  const handleRegister = async () => {
    setAuthMode("register");
    if (!authEmail && !authPassword) {
      setAuthError("Email and password are required.");
      if (!authPassword) {
        setShowPasswordTips(true);
      }
      return;
    }
    if (!authEmail) {
      setAuthError("Email is required.");
      return;
    }
    if (!authPassword) {
      setAuthError("Password is required.");
      setShowPasswordTips(true);
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
        const payload = (await resp.json().catch(() => null)) as
          | { detail?: string }
          | null;
        if (resp.status === 422 || resp.status === 400) {
          setShowPasswordTips(true);
        }
        setAuthError(payload?.detail || "Registration failed.");
        return;
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
    setAuthMode("login");
    if (!authEmail && !authPassword) {
      setAuthError("Email and password are required.");
      return;
    }
    if (!authEmail) {
      setAuthError("Email is required.");
      return;
    }
    if (!authPassword) {
      setAuthError("Password is required.");
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
        const payload = (await resp.json().catch(() => null)) as
          | { detail?: string }
          | null;
        setAuthError(payload?.detail || "Login failed.");
        return;
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
      <header className="mx-auto grid w-full max-w-6xl grid-cols-[1fr_auto] items-center px-6 pt-8 md:grid-cols-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-[conic-gradient(from_120deg,_#d7b36c,_#7dd3fc,_#d7b36c)]" />
          <div>
            {/* <p className="text-xs uppercase tracking-[0.35em] text-[color:var(--muted)]">
              CineMind
            </p> */}
            <p className="text-lg font-semibold text-[color:var(--foreground)]">
              CineMind
            </p>
          </div>
        </div>
        <nav className="hidden items-center justify-center gap-6 text-sm text-[color:var(--muted)] md:flex">
          <button
            onClick={() => setActiveTab("discover")}
            className={`cursor-pointer transition focus:outline-none focus-visible:outline-none ${
              activeTab === "discover"
                ? "text-[color:var(--foreground)]"
                : "text-[color:var(--muted)]"
            }`}
          >
            Discover
          </button>
          <button
            onClick={() => setActiveTab("my-space")}
            className={`cursor-pointer transition focus:outline-none focus-visible:outline-none ${
              activeTab === "my-space"
                ? "text-[color:var(--foreground)]"
                : "text-[color:var(--muted)]"
            }`}
          >
            My Space
          </button>
        </nav>
        <div ref={profileRef} className="relative flex items-center justify-end">
          <button
            onClick={() => {
              const next = !profileOpen;
              setProfileOpen(next);
              if (next && !authUser) {
                setAuthMode("login");
                setAuthError(null);
                setShowPasswordTips(false);
              }
            }}
            className="cursor-pointer rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)] transition focus:outline-none focus-visible:outline-none"
          >
            {authUser ? "Profile" : "Sign in"}
          </button>
          <div
            onClick={() => setProfileOpen(false)}
            className={`fixed inset-0 z-10 bg-black/40 backdrop-blur-sm transition-opacity md:hidden ${
              profileOpen ? "opacity-100" : "pointer-events-none opacity-0"
            }`}
          />
          <div
            aria-hidden={!profileOpen}
            className={`fixed left-4 right-4 top-20 z-20 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-3xl border border-white/10 bg-black/70 p-5 backdrop-blur-xl shadow-[0_18px_50px_rgba(0,0,0,0.45)] transition duration-150 md:absolute md:left-auto md:right-0 md:top-full md:mt-3 md:max-h-none md:w-72 md:overflow-visible ${
              profileOpen
                ? "translate-y-0 scale-100 opacity-100"
                : "pointer-events-none translate-y-2 scale-95 opacity-0"
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.35em] text-[color:var(--muted)]">
                  {authUser ? "Account" : authMode === "login" ? "Login" : "Register"}
                </p>
                <div className="h-2 w-2 rounded-full bg-[color:var(--accent)]" />
              </div>
              {authUser ? (
                <div className="space-y-3">
                  <div className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-xs text-[color:var(--muted)]">
                    {authUser.email}
                  </div>
                  <button
                    onClick={handleLogout}
                    disabled={authLoading}
                    className="w-full cursor-pointer rounded-2xl border border-white/10 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)] transition focus:outline-none focus-visible:outline-none"
                  >
                    {authLoading ? "Signing out..." : "Sign out"}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-[10px] uppercase tracking-[0.2em]">
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("login");
                        setAuthError(null);
                        setShowPasswordTips(false);
                      }}
                      className={`flex-1 cursor-pointer rounded-full px-3 py-1 transition focus:outline-none focus-visible:outline-none ${
                        authMode === "login"
                          ? "bg-[color:var(--accent)] text-black"
                          : "text-[color:var(--muted)]"
                      }`}
                    >
                      Login
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("register");
                        setAuthError(null);
                        setShowPasswordTips(false);
                      }}
                      className={`flex-1 cursor-pointer rounded-full px-3 py-1 transition focus:outline-none focus-visible:outline-none ${
                        authMode === "register"
                          ? "bg-[color:var(--accent)] text-black"
                          : "text-[color:var(--muted)]"
                      }`}
                    >
                      Register
                    </button>
                  </div>
                  <input
                    placeholder="Email"
                    value={authEmail}
                    onChange={(event) => setAuthEmail(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
                  />
                  <div className="relative">
                    <input
                      placeholder="Password"
                      type={showPassword ? "text" : "password"}
                      value={authPassword}
                      onChange={(event) => setAuthPassword(event.target.value)}
                      className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 pr-12 text-sm text-[color:var(--foreground)] outline-none placeholder:text-[color:var(--muted)]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute right-3 top-1/2 z-10 -translate-y-1/2 cursor-pointer rounded-full bg-white/5 p-2 text-[color:var(--muted)] transition hover:text-[color:var(--foreground)] focus:outline-none focus-visible:outline-none"
                    >
                      {showPassword ? (
                        <svg
                          viewBox="0 0 24 24"
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.6"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      ) : (
                        <svg
                          viewBox="0 0 24 24"
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.6"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M3 12s3.5-7 9-7c3.1 0 5.6 1.3 7.4 3" />
                          <path d="M21 12s-3.5 7-9 7c-3.1 0-5.6-1.3-7.4-3" />
                          <path d="M14.1 9.9a3 3 0 0 0-4.2 4.2" />
                          <path d="M3 3l18 18" />
                        </svg>
                      )}
                    </button>
                  </div>
                  {authMode === "register" && showPasswordTips && passwordTooShort ? (
                    <p className="text-xs text-[#ff8a8a]">
                      Password tip: use at least 8 characters.
                    </p>
                  ) : null}
                  <button
                    onClick={authMode === "login" ? handleLogin : handleRegister}
                    disabled={authLoading}
                    className="w-full cursor-pointer rounded-2xl bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-black transition focus:outline-none focus-visible:outline-none"
                  >
                    {authLoading
                      ? "Working..."
                      : authMode === "login"
                        ? "Login"
                        : "Register"}
                  </button>
                </div>
              )}
              {authError ? (
                <p className="text-xs text-[#ffb4a2]">{authError}</p>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-10 px-6 pb-24 pt-12 lg:grid-cols-[320px_1fr]">
        <aside className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-black/40 p-5">
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
                  onClick={() => generateFromSeeds("content")}
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
          {activeTab === "discover" ? (
            <section className="grid gap-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-[color:var(--accent)]">
                    Discover
                  </p>
                  <h2 className="text-2xl font-semibold">
                    {discoverMode === "trending"
                      ? "Hyped right now"
                      : discoverMode === "upcoming"
                        ? "Upcoming releases"
                        : "Filtered picks"}
                  </h2>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-[10px] uppercase tracking-[0.2em]">
                  <button
                    type="button"
                    onClick={() => setDiscoverMode("trending")}
                    className={`flex-1 cursor-pointer rounded-full px-3 py-1 transition focus:outline-none focus-visible:outline-none ${
                      discoverMode === "trending"
                        ? "bg-[color:var(--accent)] text-black"
                        : "text-[color:var(--muted)]"
                    }`}
                  >
                    Trending
                  </button>
                  <button
                    type="button"
                    onClick={() => setDiscoverMode("upcoming")}
                    className={`flex-1 cursor-pointer rounded-full px-3 py-1 transition focus:outline-none focus-visible:outline-none ${
                      discoverMode === "upcoming"
                        ? "bg-[color:var(--accent)] text-black"
                        : "text-[color:var(--muted)]"
                    }`}
                  >
                    Upcoming
                  </button>
                  <button
                    type="button"
                    onClick={() => setDiscoverMode("filtered")}
                    className={`flex-1 cursor-pointer rounded-full px-3 py-1 transition focus:outline-none focus-visible:outline-none ${
                      discoverMode === "filtered"
                        ? "bg-[color:var(--accent)] text-black"
                        : "text-[color:var(--muted)]"
                    }`}
                  >
                    Filtered
                  </button>
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                <div className="grid gap-3 md:grid-cols-4">
                  <input
                    placeholder="Year from"
                    value={discoverYearFrom}
                    onChange={(event) => setDiscoverYearFrom(event.target.value)}
                    className="rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                  <input
                    placeholder="Year to"
                    value={discoverYearTo}
                    onChange={(event) => setDiscoverYearTo(event.target.value)}
                    className="rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                  <input
                    placeholder="Runtime min"
                    value={discoverRuntimeMin}
                    onChange={(event) => setDiscoverRuntimeMin(event.target.value)}
                    className="rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                  <input
                    placeholder="Runtime max"
                    value={discoverRuntimeMax}
                    onChange={(event) => setDiscoverRuntimeMax(event.target.value)}
                    className="rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                  <input
                    placeholder="Cast (comma separated)"
                    value={discoverCast}
                    onChange={(event) => setDiscoverCast(event.target.value)}
                    className="md:col-span-2 rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                  <input
                    placeholder="Director (comma separated)"
                    value={discoverDirector}
                    onChange={(event) => setDiscoverDirector(event.target.value)}
                    className="md:col-span-2 rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                  />
                </div>
                {discoverGenres.length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {discoverGenres.map((genre) => {
                      const active = discoverGenreIds.includes(genre.id);
                      return (
                        <button
                          key={`genre-${genre.id}`}
                          type="button"
                          onClick={() => toggleDiscoverGenre(genre.id)}
                          className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] transition focus:outline-none focus-visible:outline-none ${
                            active
                              ? "border-[color:var(--accent)] text-[color:var(--accent)]"
                              : "border-white/10 text-[color:var(--muted)]"
                          }`}
                        >
                          {genre.name}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={applyDiscoverFilters}
                    className="cursor-pointer rounded-full bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-black"
                  >
                    Apply filters
                  </button>
                  <button
                    type="button"
                    onClick={resetDiscoverFilters}
                    className="cursor-pointer rounded-full border border-white/10 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)]"
                  >
                    Reset
                  </button>
                </div>
              </div>
              {discoverError ? (
                <p className="text-xs text-[#ffb4a2]">{discoverError}</p>
              ) : null}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {discoverLoading
                  ? Array.from({ length: 6 }).map((_, idx) => (
                      <div
                        key={`discover-${idx}`}
                        className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-white/5 p-4"
                      >
                        <div className="aspect-[2/3] rounded-2xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                        <div className="space-y-2">
                          <div className="h-3 w-2/3 rounded-full bg-white/10" />
                          <div className="h-3 w-1/2 rounded-full bg-white/10" />
                        </div>
                      </div>
                    ))
                  : discoverItems.map((item) => (
                      <div
                        key={item.tmdb_id}
                        role="button"
                        tabIndex={0}
                        onClick={() => addPick(item)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            addPick(item);
                          }
                        }}
                        className="group relative flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/5 p-4 text-left transition hover:border-white/20 hover:bg-white/10 focus:outline-none focus-visible:outline-none"
                      >
                        <div className="aspect-[2/3] overflow-hidden rounded-2xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]">
                          {item.poster_url ? (
                            <img
                              src={item.poster_url}
                              alt={item.title}
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : null}
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-[color:var(--foreground)]">
                              {item.title}
                            </p>
                            {selectedIds.has(item.tmdb_id) ? (
                              <span className="rounded-full border border-white/10 bg-black/40 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[color:var(--muted)]">
                                Added
                              </span>
                            ) : null}
                          </div>
                          <p className="text-xs text-[color:var(--muted)]">
                            {item.year || "Unknown year"}
                          </p>
                          {item.overview ? (
                            <p className="line-clamp-3 text-xs text-[color:var(--muted)]">
                              {item.overview}
                            </p>
                          ) : null}
                        </div>
                        <div className="mt-auto flex items-center justify-between gap-3">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              toggleLike(item.tmdb_id);
                            }}
                            className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] transition focus:outline-none focus-visible:outline-none ${
                              likedIds[item.tmdb_id]
                                ? "border-[color:var(--accent)] text-[color:var(--accent)]"
                                : "border-white/10 text-[color:var(--muted)]"
                            }`}
                          >
                            <svg
                              viewBox="0 0 24 24"
                              className="h-3 w-3"
                              fill={
                                likedIds[item.tmdb_id]
                                  ? "currentColor"
                                  : "none"
                              }
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="M20.8 5.7c-1.5-1.6-4-1.6-5.5 0L12 9l-3.3-3.3c-1.5-1.6-4-1.6-5.5 0-1.8 1.8-1.6 4.6.2 6.3L12 21l8.6-9c1.8-1.7 2-4.5.2-6.3Z" />
                            </svg>
                            Like
                          </button>
                          <div className="flex items-center gap-1">
                            {Array.from({ length: 5 }).map((_, idx) => {
                              const value = idx + 1;
                              const active = (ratings[item.tmdb_id] || 0) >= value;
                              return (
                                <button
                                  key={`${item.tmdb_id}-rating-${value}`}
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    setRating(item.tmdb_id, value);
                                  }}
                                  className={`transition focus:outline-none focus-visible:outline-none ${
                                    active
                                      ? "text-[color:var(--accent)]"
                                      : "text-white/30"
                                  }`}
                                >
                                  <svg
                                    viewBox="0 0 24 24"
                                    className="h-3.5 w-3.5"
                                    fill={active ? "currentColor" : "none"}
                                    stroke="currentColor"
                                    strokeWidth="1.4"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  >
                                    <path d="M12 3.5 14.6 8l5.1.8-3.7 3.7.9 5.1L12 15.8 7.1 17.6l.9-5.1-3.7-3.7 5.1-.8L12 3.5Z" />
                                  </svg>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ))}
              </div>
            </section>
          ) : (
            <>
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
              <input
                value={hybridYearFrom}
                onChange={(event) => setHybridYearFrom(event.target.value)}
                placeholder="Year from"
                className="rounded-full border border-white/10 bg-black/30 px-4 py-2 text-xs text-[color:var(--foreground)]"
              />
              <input
                value={hybridYearTo}
                onChange={(event) => setHybridYearTo(event.target.value)}
                placeholder="Year to"
                className="rounded-full border border-white/10 bg-black/30 px-4 py-2 text-xs text-[color:var(--foreground)]"
              />
              <button
                onClick={randomizeUser}
                className="cursor-pointer rounded-full border border-white/10 px-4 py-2 text-xs font-semibold text-[color:var(--foreground)]"
              >
                Random user
              </button>
              <button
                onClick={() => refreshHybrid()}
                className="cursor-pointer rounded-full bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-black"
              >
                {hybridLoading ? "Loading" : "Regenerate"}
              </button>
            </div>
          </div>
          {likedError ? (
            <p className="text-xs text-[#ffb4a2]">{likedError}</p>
          ) : null}
          <div className="grid gap-4 md:grid-cols-6">
            {likedLoading
              ? Array.from({ length: 6 }).map((_, idx) => (
                  <div
                    key={`liked-${idx}`}
                    className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                    <div className="space-y-1">
                      <div className="h-3 w-2/3 rounded-full bg-white/10" />
                      <div className="h-3 w-1/2 rounded-full bg-white/10" />
                    </div>
                  </div>
                ))
              : likedMovies.length === 0
                ? Array.from({ length: 3 }).map((_, idx) => (
                    <div
                      key={`liked-empty-${idx}`}
                      className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                    >
                      <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                      <div className="space-y-1">
                        <p className="text-xs text-[color:var(--muted)]">
                          No likes yet
                        </p>
                      </div>
                    </div>
                  ))
                : likedMovies.map((item) => (
                    <div
                      key={`liked-${item.movie_id}`}
                      className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                    >
                      <div className="aspect-[2/3] overflow-hidden rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]">
                        {item.poster_url ? (
                          <img
                            src={item.poster_url}
                            alt={item.title || "Liked movie"}
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
                          Rated {item.rating.toFixed(1)}
                        </p>
                      </div>
                    </div>
                  ))}
          </div>
          {hybridError ? (
            <p className="text-xs text-[#ffb4a2]">{hybridError}</p>
          ) : null}
          <div className="grid gap-4 md:grid-cols-5">
            {hybridLoading
              ? Array.from({ length: 5 }).map((_, idx) => (
                  <div
                    key={`row-loading-${idx}`}
                    className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                    <div className="space-y-1">
                      <div className="h-3 w-2/3 rounded-full bg-white/10" />
                      <div className="h-3 w-1/2 rounded-full bg-white/10" />
                    </div>
                  </div>
                ))
              : hybridResults.length === 0
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
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={seedYearFrom}
                  onChange={(event) => setSeedYearFrom(event.target.value)}
                  placeholder="Year from"
                  className="rounded-full border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                />
                <input
                  value={seedYearTo}
                  onChange={(event) => setSeedYearTo(event.target.value)}
                  placeholder="Year to"
                  className="rounded-full border border-white/10 bg-black/30 px-3 py-2 text-xs text-[color:var(--foreground)]"
                />
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
            </div>
            <div className="grid gap-4 md:grid-cols-5">
              {seedLoading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <div
                    key={`seed-loading-${idx}`}
                    className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="aspect-[2/3] rounded-xl bg-gradient-to-br from-[#241c2b] via-[#17232d] to-[#101015]" />
                    <div className="space-y-1">
                      <div className="h-3 w-2/3 rounded-full bg-white/10" />
                      <div className="h-3 w-1/2 rounded-full bg-white/10" />
                    </div>
                  </div>
                ))
              ) : seedResults.length === 0
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
            </>
          )}
        </div>
      </main>
    </div>
  );
}
