from __future__ import annotations

import argparse

from ml.config import DATA_DIR
from ml.training.io import get_user_ratings


def main() -> None:
    parser = argparse.ArgumentParser(description="Show a user's rated movies")
    parser.add_argument("user_id", help="MovieLens user ID")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to print")
    args = parser.parse_args()

    rows = get_user_ratings(
        user_id=args.user_id,
        ratings_path=DATA_DIR / "rating.csv",
        movies_path=DATA_DIR / "movie.csv",
        limit=args.limit,
    )

    for row in rows:
        print(f"{row['movie_id']}\t{row['rating']}\t{row['title']}")


if __name__ == "__main__":
    main()
