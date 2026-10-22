# Purdue Astronomy Club website

A complete Hugo public website for `https://purdueastro.club/`, built for GitHub Pages and maintained through [Pages CMS](https://app.pagescms.org/).

**Start here:** [Launch instructions for GitHub + Porkbun + CMS](docs/LAUNCH_GUIDE.md). For routine editing, use the [Officer Guide](docs/OFFICER_GUIDE.md). See [TEST_REPORT](docs/TEST_REPORT.md) for verified work and remaining account-bound checks.

The site includes the Dark Celestial homepage, public information pages, shared event/astronomy calendar with mobile agenda and ICS, event albums, astrophotography, news, officer/sponsor profiles, editable global settings, client-side photo preparation, and optional PNG/PDF calendar export. No genuine event dates, names, contacts, sponsor relationships or astrophotographs were fabricated. One unpublished event demonstrates the form.

## Automatic sky calendar

The website automatically adds four lunar phases, Mars–Neptune oppositions, equinoxes/solstices, and dated AMS meteor-shower peak nights. Original SVG icons distinguish phases, individual planets, meteors, and seasonal events. The same normalized records drive the website, SSR fallback, detail pages, ICS and printable exports. CMS **Automatic Sky Calendar** controls categories, rolling year range, and per-entry suppression. Officer-written astronomy can replace calculated records without duplication.

Astronomy Engine **2.1.19** calculates the ephemeris locally; no runtime API or paid key is required. The previous/current/next years are calculated by default. `scripts/refresh_meteors.py` parses only explicit dated peak-night facts from the official AMS calendar. The checked-in `data/astronomy/meteor-showers.json` supplies a verified starting snapshot; production Actions preserves `.generated/meteor-cache.json` between successful builds and refreshes it at most once per UTC date. An unavailable or changed source falls back to dated cached data and exposes its check date; forecasts older than 30 days are flagged. Future meteor dates are never inferred from a previous year.

`data/astronomy.yml` stores CMS controls. `scripts/automatic_sky.py` emits normalized entries plus ignored `.generated/content/astronomy` Markdown, mounted into Hugo's astronomy section. Generated details retain stable event references; manual `replaces_auto_event` or matching kind/planet/date avoids duplicate entries. A precise UTC event remains unambiguous through DST; ICS preserves its calculated instant. Calculated events are one-minute markers, not one-hour club activities. Set `PAC_OFFLINE=1` for a deterministic build using the retained source snapshot/cache.

Moon calculations for all 50 phases in 2026 were checked against the independent [USNO data service](https://aa.usno.navy.mil/data/MoonPhases) with a five-minute tolerance. A fixture of that official 2026 JSON is kept under `tests/fixtures`. Calculations remain approximate and do not establish local visibility. Meteor entries identify evening-to-morning forecast windows. Eclipses or other local/special phenomena can still be added as verified CMS highlights.

## Automatic Drive gallery

The selected club folder is configured in `data/drive_gallery.yml`. **Ten actual member photos are already included**, credited to Sam Guber, and all appear in the rotating homepage gallery. Their optimized, metadata-free launch copies are in `assets/drive-gallery-snapshot`; a fresh checkout/build displays them without Google credentials. Automatic refreshing starts disabled until the owner adds the Google service-account JSON as the `DRIVE_GALLERY_CREDENTIALS_JSON` GitHub Actions secret and enables **Drive Gallery Settings** in Pages CMS. Follow [the complete Drive setup guide](docs/DRIVE_GALLERY_SETUP.md).

`firstname_lastname_target_words.jpg` becomes **Target Words**, credited **Image by Firstname Lastname**. `scripts/sync_drive_gallery.py` reads only direct children of the configured folder, supports pagination/shared drives, and downloads JPEG/PNG/WebP blobs with read-only access. It preserves stable hashed page references across renames, applies optional CMS title/credit/alt/caption/hidden corrections, and writes generated astrophotography content mounted into Hugo. Imported originals never enter Git. Only oriented, resized, metadata-free WebP copies enter the included launch snapshot or ignored `.generated/drive-gallery` cache and image pipeline. A completed live sync replaces the initial snapshot and withdraws files removed from the folder without duplicates; an incomplete listing or failed download stops deployment and preserves the previous live site. Offline/PR builds skip Drive and use the included launch photos when `use_snapshot` is on. To withdraw all Drive photography, turn off both live importing and the initial-photo setting in CMS.

The homepage carousel includes every published astrophotograph and every photo in published event albums, without a Featured requirement. It shows three cards on desktop, two on tablets and one on phones, advances every five seconds while visible, and wraps through the complete set. Previous/Next, keyboard arrows/Home/End and native touch scrolling are available; there is no pause button. The scrollbar is hidden; hovering and ordinary page scrolling do not stop rotation. Rotation holds while keyboard focus is in the carousel and resumes when focus leaves. Reduced-motion preferences disable automatic rotation. Without JavaScript, the complete row remains scrollable and its photo links still work. The carousel uses local CSS/JavaScript and adds no package dependency. **Homepage Settings → Show the gallery carousel** controls its visibility.

Production refreshes every six hours and on manual builds/CMS saves. No Drive credential is exposed to PR checks, visitor browsers, or the delivery ZIP. Manual CMS showcases remain available. A follow-up check found ten photos in **Member_Photos**. Drive imports accept originals up to 200 MB/120 megapixels and resize before the shared image pipeline; manual CMS uploads keep their 15 MB limit. Live unattended authentication/import acceptance remains an owner task. A standard API key cannot replace the service-account JSON credential for restricted folder access.

## Officers

The eight **2026–27 officer core** profiles, portraits, roles, class years and majors are included from the club’s [existing People page](https://sites.google.com/view/purduepac/people). Both published Treasurer roles were retained. Photos are local metadata-free WebP assets, so Google Sites is not needed at runtime. Edit each person in **Pages CMS → Club Officers**, and change the academic year/introduction in **Officer Page Settings**. Clicking a name opens its full profile.

## Local build

Tested with Hugo extended **0.168.0**, Python **3.14.4** locally (CI uses **3.12**), Node **22.22.1**, FullCalendar Standard **6.1.20**, Playwright **1.64.1**, and axe **4.14.0**. Python dependencies are pinned in `requirements-ci.txt`; Node dependencies are locked in `package-lock.json`. Font stacks use system sans-serif and Georgia; no third-party font service is required. FullCalendar's MIT license is retained next to the vendored bundle.

Install Hugo extended 0.168.0 from its official releases, or use the checksum-verifying Linux installer:

```bash
bash scripts/install-hugo.sh
export PATH="/tmp/pac-hugo:$PATH"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ci.txt
python scripts/build.py
python -m http.server 1313 --bind 127.0.0.1 --directory public
```

Open `http://127.0.0.1:1313/`. After content changes, run `python scripts/build.py` again and refresh. Do not use a bare Hugo build for final output: it needs the normalization and image steps first. After the build helper has run, `hugo server --bind 127.0.0.1 --port 1313` also works for template/CSS development; rerun the helper after event/data changes.

## Checks

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python scripts/build.py
npm ci
npx playwright install chromium firefox
npm run test:browser
```

Linux browser dependencies can be installed with Playwright’s `--with-deps` flag when needed. Tests use synthetic data in temporary directories or intercepted browser responses. They never publish fixture events into the production source. The full integration test needs Hugo in PATH (otherwise it explicitly skips).

To upgrade the calendar dependency intentionally, update its exact version, run `npm install`, then `npm run vendor`. Commit the lockfile, copied bundle and retained license together. Re-test before shipping. The deployed site uses the copied bundle; no npm or CDN is needed at runtime.

## Source layout and data flow

- `.pages.yml`: officer-facing schemas, safe Draft defaults, stable filenames, ordered photo objects, settings, and the optional export action.
- `content/`: CMS Markdown records with YAML front matter.
- `data/home.yml`, `data/site.yml`, `data/calendar/banners.yml`: CMS settings.
- `scripts/content.py`: validation and the single normalized event model.
- `scripts/build_calendar.py`: normalized Hugo data, `/events.json`, `/months.json`, `/calendar.ics`, and per-event invitations.
- `scripts/optimize_images.py`: metadata-free WebP derivatives and image dimensions/srcsets; sanitized production copies of source images.
- `layouts/`, `assets/`: reusable templates, handcrafted styles and small progressive enhancements.
- `scripts/validate_public_output.py`: generated-output draft/private-reference scan and internal link/media checks. Optional `FORBIDDEN_PUBLIC_HOSTS` is a comma-separated CI variable; do not put private infrastructure names into public content.
- `public/`, `data/generated/`, `static/media/`, generated feeds/invitations, `.generated/`: ignored build outputs.

Calendar records have stable IDs derived from saved filenames. CMS end dates are inclusive; all-day ICS/FullCalendar ends are exclusive. Timed records use Indiana `zoneinfo` conversion, explicit ISO offsets, and UTC ICS timestamps. Ambiguous/nonexistent DST wall times fail with an explanatory error. Timed events without an end time get a one-hour invitation duration. The browser uses floating Indiana wall-clock copies for display so visitor time zones cannot shift events. Original explicit offsets remain in JSON/ICS. Postponed events retract the original ICS slot and clearly label that date as original; cancellations preserve UIDs. Keep files stable and use aliases for any maintainer-led URL change.

Hugo’s frontmatter configuration maps `publish_date` to PublishDate, so future news is excluded until a later build. The scheduled workflow refreshes date-sensitive output. Album ordering uses event date; officers/sponsors use explicit order.

## Deployment and export

`.github/workflows/hugo-pages.yml` reads the actual GitHub Pages address with `actions/configure-pages`, validates, tests, builds and deploys on pushes to `main`, manual runs, and every six hours at 00:17, 06:17, 12:17 and 18:17 UTC. AMS refresh remains limited to once per UTC day. Pull requests get offline content/build and browser checks. The deploy job alone has Pages-write and OIDC permissions; the production build alone receives the optional Drive secret.

`export-calendar.yml` accepts a Pages CMS `payload` string, reads its `inputs.month` as data, validates the month, and exports the shared poster route to 1920×1080 PNG and A3 landscape PDF artifacts. It does not commit graphics or expose a public workflow trigger. Dense months fail rather than silently crop. Local export after building/serving: `node scripts/export-calendar.mjs 2026-10`.

GitHub Pages project hosting at `https://purdue-astronomy-club.github.io/website/` works before the custom domain is ready. `HUGO_BASEURL` controls generated assets, page links, calendar JSON/icons, redirects and invitation URLs; Actions obtains it from the Pages setting. After changing the Pages custom domain, run the complete build workflow again so all generated paths match the new address. For a manual project-path build, run `HUGO_BASEURL=https://purdue-astronomy-club.github.io/website/ python scripts/build.py` and serve the resulting output at `/website/`. The normal local preview uses the root-path default.

Initial account setup, live CMS saves/uploads, GitHub Actions, domain verification and HTTPS must be completed by an owner with the necessary access. Those are documented, not claimed as completed.
