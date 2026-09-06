# Portal Themes

Public theme catalog shared by the Mikro Wave and Ruijie apps. Both apps fetch
`manifest.json` from this repo's `main` branch over `raw.githubusercontent.com`
and cache it locally, so anything committed and pushed here reaches every
install of either app.

The two apps apply a theme very differently, so each theme generates **two**
sibling file sets from the same `THEMES` entry:

- `themes/<id>/<version>/` — Mikrotik-style `$(variable)`-templated router
  pages (`login.html`, `alogin.html`, `redirect.html`, `status.html`), used
  by Mikro Wave.
- `ruijie/<id>/<version>/` — a Ruijie Cloud custom-portal bundle
  (`index.html` + `loadConfig.json`), used by the voucher_maker (Ruijie) app.
  Ruijie portals aren't router-templated HTML; they're a small single-page
  app that calls Ruijie's `/api/auth/general` and get zipped together with a
  background image and uploaded as a custom portal. `index.html` keeps a
  `{{PACKAGES_SECTION}}` token that the app fills in with the merchant's
  actual voucher package/price list at apply-time — don't remove it.

## Adding or editing a theme

All theme design lives in one place: the `THEMES` list in
`tools/generate_themes.py`. Don't hand-edit files under `themes/`, `ruijie/`,
or the corresponding entries in `manifest.json` — they're generated output
and get overwritten the next time the generator runs.

1. Edit or add an entry in `THEMES` (colors, typography, `layout`).
   - **To publish a redesign of an existing theme, bump its `version`**
     (e.g. `"1.0.0"` → `"1.1.0"`). The generator only ever writes to
     `themes/<id>/<version>/` and `ruijie/<id>/<version>/` — it never deletes
     an older version's folder, because an app in the field may have already
     cached a manifest that still points at those exact files, and yanking
     them out from under it would break that user's already-applied portal
     page. Reusing an existing version number is fine while you're iterating
     locally before you've pushed, but treat any version you've pushed to
     `main` as permanent.
   - A brand-new theme just needs a new `id` (must match
     `^[a-z0-9][a-z0-9-]{1,48}$`) starting at whatever version you like. Its
     Ruijie portal reuses the `dark` layout's card styling until you add a
     matching function to `RUIJIE_LAYOUTS` in `tools/generate_themes.py`.
2. Run `python tools/generate_themes.py`. This regenerates that theme's
   `login.html` / `alogin.html` / `redirect.html` / `status.html` and its
   `ruijie/` `index.html` / `loadConfig.json`, re-renders `preview.png` and
   `preview-overlay.png` from the real Mikrotik HTML via headless Chrome (a
   360×640 viewport, with `{{SHOP_NAME}}` substituted with `Shop Name` so
   previews stay brand-neutral for whichever app is browsing the catalog —
   Ruijie has no separate preview and reuses these same images), and
   rewrites `manifest.json`'s `themes` list from `THEMES`.
   - Needs a Chrome/Chromium/Edge install. It's found automatically in the
     usual places; if yours is somewhere else, set `CHROME_PATH`.
   - Needs `pip install Pillow`.
   - No local Chrome? Run the **Theme catalog** GitHub Actions workflow
     manually instead (Actions tab → "Theme catalog" → "Run workflow", with
     "commit" checked) — it installs Chrome itself, regenerates everything,
     and pushes the result. See [CI](#ci) below.
3. Run `python tools/validate_manifest.py` and fix anything it flags before
   committing — see [Validating the manifest](#validating-the-manifest).
4. Commit and push both the generator change and the regenerated
   `themes/`/`ruijie/`/`manifest.json` output together.

## Backgrounds

Backgrounds are independent from themes and aren't part of `THEMES` — add
them directly to `manifest.json`. Give each image any file name inside
`images/`, then add it to the top-level `backgrounds` list:

```json
"backgrounds": [
  {
    "id": "blue-sky",
    "name": "Blue Sky",
    "version": "1",
    "enabled": true,
    "image": "images/my-background-name.jpg"
  }
]
```

The app lets users search this list by `name` and combine any background with
any theme.

## Validating the manifest

Both apps parse `manifest.json` with a small, strict Dart parser, and it is
stricter than it looks: a missing or blank required field on **any one**
enabled theme (or background) entry throws while parsing, and the app's
catch-all turns that into an **empty list for the entire catalog** — not
just the one broken entry. An invalid `id` or a malformed `colors`/`files`
value is more forgiving and just skips that one entry.

`tools/validate_manifest.py` checks `manifest.json` against these exact
rules — including whether every `preview`/`previewOverlay`/`files.*`/`image`
path it references actually exists in the repo — and reports which failure
mode you're looking at:

```
python tools/validate_manifest.py            # errors fail the run; warnings are just printed
python tools/validate_manifest.py --strict    # warnings fail the run too (what CI uses)
```

Run it after `generate_themes.py`, and before every commit that touches
`manifest.json` by hand (e.g. adding a background).

## CI

`.github/workflows/theme-catalog.yml` runs on every push/PR that touches the
generator, `manifest.json`, or `themes/**`:

- Regenerates everything and fails if that leaves uncommitted changes — the
  signal that someone edited `THEMES`, a theme HTML file, or `manifest.json`
  by hand and forgot to run the generator, or committed generated output
  that's stale relative to the generator.
- Runs `validate_manifest.py --strict` unconditionally.

It also supports **Run workflow** from the Actions tab with the "commit" box
checked, which regenerates everything using a Chrome CI installs itself and
pushes the result directly — the easiest way to publish a theme change
without installing anything locally.
