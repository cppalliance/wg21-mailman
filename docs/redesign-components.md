# WG21 Mailman Redesign - Shared Component Proposal

Turns the redesign mockups into ONE shared component system so Postorius and HyperKitty
render identical chrome from a single source. Design tokens live in `[../DESIGN.md](../DESIGN.md)`;
vocabulary in `[../CONTEXT.md](../CONTEXT.md)`.

## Target repo & deployment

- Ships in this repo (`wg21-mailman`). The `wg21/`, `postorius/`, and `hyperkitty/` trees (templates + shared static) now exist; the base overrides (`{postorius,hyperkitty}/base.html`) plus the two index pages carry the redesign. Note: auth/account/profile pages inherit the theme automatically because `account/base.html` and `django_mailman3/base.html` extend the overridden app `base.html` files.
- Production: `settings.py` registers `STATICFILES_DIRS=[BASE_DIR/static_custom]` and `TEMPLATES[0]['DIRS']=[BASE_DIR/templates]`; `ansible/custom-wg21/main.yml` copies repo `{postorius,hyperkitty}/static/...` -> `static_custom/` and `.../templates/...` -> `templates/`, then runs `collectstatic` + `compress`. Overrides win by finder/loader precedence (no site-packages hijacking).
- A `wg21/` shared namespace is added as one more ansible copy entry into `static_custom/` + `templates/`.



## Local development

- Self-contained `docker-compose.yml` in this repo using `maxking/mailman-core` + `maxking/mailman-web` images (postgres + core + web), with `local/urls.py` (prod URL paths) and `local/uwsgi.ini` (serves `/static` without nginx).
- Mounts a local settings shim (`local/settings_local.py`) that sets `DEBUG=True` and enables `STATICFILES_DIRS=[static_custom]` + `TEMPLATES DIRS=[templates]` (prod-faithful; the prod `settings.py` contains ansible Jinja `{% if %}` that cannot run raw locally). Under Django 4.1+ the default template config ALWAYS wraps loaders in `cached.Loader` regardless of `DEBUG` (only `runserver`'s autoreload signal clears that cache, and uWSGI does not raise it), so the shim also sets `TEMPLATES[0]['OPTIONS']['loaders']` explicitly and flips `APP_DIRS=False` - this bypasses the cached wrapper and gives real live template reload on browser refresh.
- Static serving: the fully-custom `wg21/` namespace is served live from its bind mount via a dedicated `static-map = /static/wg21=/opt/wg21-custom/static_custom/wg21` in `local/uwsgi.ini`. Edit a `wg21/` CSS/img file and hard-refresh; no `collectstatic` step. Stock app static (bootstrap, fonts, JS) is populated in `STATIC_ROOT` by the image entrypoint on start. Templates live-reload via `TEMPLATES DIRS` under `DEBUG=True`. (There is intentionally no symlink/`collectstatic --link` workflow.)
- Adding a per-app static override later (a real file under `postorius/static/postorius/...` or `hyperkitty/static/hyperkitty/...`): add its bind mount in `docker-compose.yml` and, if you want it served live, an analogous specific `static-map` line; otherwise rely on the entrypoint `collectstatic`.



## Overriding a new page (copy-to-tweak)

- To customize a page you have not overridden yet, copy the version-matched upstream template into this repo's `DIRS` tree, preserving the app subdir (e.g. `hyperkitty/templates/hyperkitty/overview.html`, `postorius/templates/postorius/...`), then edit in place. Everything you do not copy keeps resolving from the installed package.
- Copy from the version-matched source: the running container's site-packages (HyperKitty 1.3.12 / Postorius 1.3.13 for the `0.5.2` images), e.g. `docker compose exec mailman-web cat /usr/lib/python3.12/site-packages/hyperkitty/templates/hyperkitty/overview.html`. Do NOT copy from an unpinned `../hyperkitty` master checkout. Record the upstream version so the file can be re-diffed on upgrade.
- Find a template: URL -> `name=` in the app's `urls.py` -> view -> template name. Example: `/archives/list/<fqdn>/` -> `hk_list_overview` -> `mlist.overview` -> `hyperkitty/overview.html`.
- `overview.html` already `{% extends "hyperkitty/base.html" %}`, so it inherits WG21 chrome; reskin inside `{% block content %}` and keep the tab anchors (`#most-recent`, `#most-active`, ...) plus the fragment includes so the async thread-loading JS keeps working.



## Delivery architecture (CSS classes + shared template partials)

- Shared namespace `wg21/`: CSS at `static_custom/wg21/css/{theme,components}.css`; partials at `templates/wg21/*.html`.
- CSS = plain CSS (no SCSS), loaded last in each app `base.html` (HyperKitty after `{% endcompress %}`, Postorius after its Bootstrap) so it overrides by cascade.
- Each app keeps its existing Bootstrap (Postorius CDN 5.0.2; HyperKitty bundled). No version unification now.
- Django `{% include %}` cannot wrap child markup, so:
  - Self-contained pieces -> parameterized partials (`{% include 'wg21/navbar.html' with ... %}`).
  - Structural wrappers (frame, table panel) -> CSS classes + a documented markup skeleton.



## Reskin scope (two-tier)

- Global base theme on ALL pages of both apps: tokens, the four fonts, navbar, footer, buttons, inputs, gold-frame primitive.
- Page components only on mocked pages: hero variants, both toolbars, ornate framed table.



## Page mapping

- Mockup "Archives View" -> HyperKitty `index.html` (sort modes, hide inactive/private, find-list search, activity column already exist -> visual reskin).
- Mockup "Home Page" logged-in (title hero + role tabs) and anonymous (subscribe CTA hero) -> Postorius `list_index` (site root redirects here).



## Component catalog

Anatomy -> class / partial -> variants -> consumer.

- Utility bar (black top strip), links active=gold -> partial `wg21/utility_bar.html`, `.wg21-utilitybar`, `.wg21-utilitybar__link--active` -> both base templates. Links use placeholder URLs (`https://example.com`) for now.
- Primary navbar (navy gradient): emblem + wordmark, breadcrumb chevron, search, avatar -> partial `wg21/navbar.html` (params: brand_url, breadcrumb_label, show_search, search_action, user) -> both base templates.
- Gold rule / divider -> `.wg21-rule--gold`.
- Ornamental frame (gold double border + Greek-key corners) -> `.wg21-frame` (+ `--marble`) + markup skeleton -> **table panel** (not yet shipped on hero).
- Hero scooped double-gold frame -> partial `wg21/hero_frame.html`; spans `.wg21-hero__frame-scoop` (page-bg corner covers), `.wg21-hero__frame-gap` (surface gap ring), `.wg21-hero__frame` (outer stroke), `.wg21-hero__frame-inner` (inner hairline). Corners are **scoop** (concave), not Greek-key; stroke colour is `--wg21-gold-border`. Knobs on `.wg21-hero`: `--wg21-hero-frame-*`. -> Postorius `index.html`, HyperKitty `index.html` (via `{% include 'wg21/hero_frame.html' %}`).
- Hero - title variant (emblem + serif title + subtitle) -> inline markup in each app's `index.html` + `wg21/hero_emblem.html` (not yet split into `wg21/hero_title.html`) -> HyperKitty index, Postorius list_index (logged-in).
- Hero - CTA variant (eyebrow + title + email input + SIGN UP + link + emblem) -> inline markup in Postorius `index.html` (not yet split into `wg21/hero_cta.html`) -> Postorius list_index (anonymous). NOTE: SIGN UP wiring is deferred feature work.
- Eyebrow label (gold rule + uppercase) -> `.wg21-eyebrow`.
- Filter toolbar - BOTH variants:
  - (a) segmented role tabs (Owner/Moderator/Member/Non-Member/All) -> `.wg21-segmented` (+ `.wg21-toolbar__label` gold pill). Role filtering is deferred feature work; ships as static shell first.
  - (b) "Hide" + checkboxes (Inactive/Private) + "Most Popular" sort dropdown -> `.wg21-toolbar`, `.wg21-check`, `.wg21-sort` -> maps to existing HyperKitty controls.
- Data table / list panel (ornate framed table, navy serif header, Greek-key side ornaments). Columns vary: List Name, Description, [Recent Activity], Last Update, Actions -> `.wg21-panel`, `.wg21-table`, `.wg21-table__head` + markup skeleton; optional `wg21/panel_chrome.html` for frame/ornament chrome -> Postorius lists, HyperKitty lists.
  - Responsive: desktop table unchanged; below `--wg21-bp-md` each `<tr>` collapses to a stacked label/value block (`data-label` `::before`); frame stays, ornaments hide/shrink.
- Buttons: navy "View" (primary), cream outline "Subscribe", gold "SIGN UP" (cta), gold active pill -> `.wg21-btn` + `--primary/--outline/--gold`; mapped onto Bootstrap `.btn`.
- Inputs: email (light bordered), search (dark-on-navy) -> `.wg21-input`, `--search`, `--on-navy`.
- Avatar (gold circle + glyph) -> `.wg21-avatar` -> navbar.
- Breadcrumb (chevron) -> `.wg21-breadcrumb` -> navbar.
- Sort dropdown -> `.wg21-sort` (Bootstrap dropdown skin) -> toolbar.
- Link-with-icon -> `.wg21-linkicon` -> hero CTA.
- Footer (marble strip: source link / muted center / rights) -> partial `wg21/footer.html`, `.wg21-footer` -> both base templates.
- Emblem (envelope + laurel) -> partial `wg21/emblem.html` (size sm/md/lg) backed by SVG -> navbar, heroes. Placeholder until official mark supplied.



## Deferred feature work (NOT in the visual-reskin pass)

- Role-based filter tabs on Postorius list_index (needs view/logic).
- Inline per-row Subscribe button on the index.
- Email SIGN UP CTA submission.
These may ship as non-functional static shells styled with the components above, but not wired.



## Assets (DELIVERED - raster PNG)

Provided files (to be copied into repo static at `wg21/static/wg21/img/`, deploying to `static_custom/wg21/img/`):

- Emblem (envelope + laurel + WG21 wordmark) -> `wg21/img/emblem.png`. Used by `wg21/emblem.html` at nav/hero sizes. (SVG version desirable later for crisp scaling.)
- Greek-key meander strip -> `wg21/img/greek-key.svg`. Used as repeating side/corner ornament for `.wg21-frame` **table panel** (not used by the hero scooped frame).
- Marble surface -> `wg21/img/marble-bg.png` / `hero-marble.png`. Used by `.wg21-hero__emblem` (marble panel) + `.wg21-footer`; not used as a frame ornament on the hero border.
- FLAG: the delivered `marble-bg` sample has decorative Greek-key arcs + a centered framed emblem baked in - confirm whether it's the full hero background art or a tileable texture; a clean arc-free marble tile may be wanted for the footer.



## Upstream sources & override targets

- Upstream canonical sources (copy-from when overriding): [https://gitlab.com/mailman/postorius](https://gitlab.com/mailman/postorius) and [https://gitlab.com/mailman/hyperkitty](https://gitlab.com/mailman/hyperkitty)
- Prod install confirms the original template trees at `/opt/mailman3/lib/python3.12/site-packages/{postorius,hyperkitty}/templates/`. Override = drop a same-named file under this repo's `templates/postorius/...` or `templates/hyperkitty/...` (the `TEMPLATES` DIR); it wins by loader precedence.
- Confirmed override targets:
  - Postorius `list_index` -> `postorius/index.html` (mockups 1 & 3). List summary -> `postorius/lists/summary.html`.
  - HyperKitty archives overview -> `hyperkitty/index.html` (Archives View mockup).
  - Global chrome tier (login/account/profile pages extend these): `postorius/base.html`, `hyperkitty/base.html`, and possibly `account/base.html` + `django_mailman3/base.html` in each tree.



## Open items

- Exact token hex values vs Figma/asset files (see DESIGN.md note).



## Suggested build sequence (tracer-bullet)

1. Scaffold `wg21-mailman` trees: `postorius/`, `hyperkitty/`, `wg21/` (static + templates) + local `docker-compose.yml` + settings shim; verify it boots and serves the unstyled apps.
2. Global base theme: `wg21/css/theme.css` (tokens/fonts) + `components.css` base (navbar/footer/buttons/inputs/frame) + shared `navbar`/`footer`/`utility_bar` partials wired into both base templates. Verify chrome on all pages.
3. HyperKitty index reskin (hero title + toolbar (b) + framed table) - all existing behavior.
4. Postorius list_index reskin (hero title/CTA shells + framed table; toolbar (a) static shell).
5. Responsive pass + ansible `wg21/` copy entry + docs.

