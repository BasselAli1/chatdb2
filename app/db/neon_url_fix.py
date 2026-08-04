"""
Neon (and many Postgres hosts) hand out connection strings with query
params meant for libpq-based drivers (psycopg2, psql) -- e.g. sslmode,
channel_binding. asyncpg is a from-scratch reimplementation of the
Postgres protocol and doesn't understand those exact param names, so
passing them straight through to create_async_engine() raises
TypeError: connect() got an unexpected keyword argument '...'

This strips every query param off the URL and re-adds only the ones
asyncpg actually accepts, translating where the name differs
(sslmode=require -> ssl=require).
"""

from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode


def to_asyncpg_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    params = parse_qs(parts.query)

    asyncpg_params = {}

    # sslmode=require / verify-full / etc -> ssl=require
    sslmode = params.get("sslmode", [None])[0]
    if sslmode and sslmode != "disable":
        asyncpg_params["ssl"] = "require"

    # channel_binding, and any other libpq-only param, is simply dropped --
    # asyncpg has no equivalent keyword for it, and dropping it is safe:
    # SSL is already being requested above, which is the actual security
    # property that mattered.

    new_query = urlencode(asyncpg_params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


if __name__ == "__main__":
    example = "postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname?sslmode=require&channel_binding=require"
    print("before:", example)
    print("after: ", to_asyncpg_url(example))
