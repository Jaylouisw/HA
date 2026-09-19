# HAGrid has moved 🔌 → [github.com/jaylouisw/hagrid](https://github.com/jaylouisw/hagrid)

**This repository is no longer where HAGrid lives.** Install it from its own repository, which has the
layout HACS requires and a published release:

1. HACS → ⋮ → **Custom repositories**
2. Add `https://github.com/jaylouisw/hagrid` — category **Integration**
3. Search for **HAGrid** → **Download**
4. Restart Home Assistant, then **Settings → Devices & Services → Add Integration → HAGrid**

## Why

HACS reads `custom_components/` at a repository's **root**. Here the integration sat at
`HAGrid/custom_components/hagrid` — two levels down, where HACS never looks — so HACS could never offer
it from this repository (issue #2). The `zip_release` / `hagrid.zip` asset declared in the old
`HAGrid/hacs.json` was never attached to any release either.

## About the copy in this repository

`HAGrid/` here is the pre-1.1.0 copy. It is **stale and unmaintained**, and it contains the bug reported
as issue #3 — a Python dataclass field-order error that made every module fail to import, so Home
Assistant could not register the config-flow handler and reported *"Invalid handler specified"*. That fix
and everything after it live only in [jaylouisw/hagrid](https://github.com/jaylouisw/hagrid).

Nothing in this repository is needed to install or run HAGrid. The other integration previously
published from here (HAIMish) was retired on 2026-09-19.

## Licence

MIT — see [HAGrid/LICENSE](HAGrid/LICENSE).
