# Reels Maker — MASTER PLAN 2.0: jeden połączony plan 2026–2027

> **JEDYNE NADRZĘDNE ŹRÓDŁO PRAWDY dla rozwoju motion design, autonomicznych mediów, SVG, audio, animowanych danych i social media.** Aktualizacja 24.10.2026 (`e8f9bd3a` na `main`). Źródła połączenia: `PRO_MOTION_ROADMAP_2026.md` + `DATA_MOTION_DESIGN.md`; poprzedni plan archiwizowany w `MASTER_PLAN_LEGACY_V1.md`.

## A. Cel i stan projektu

**Produkt docelowy:** z krótkiego briefu LLM generuje Creative Intent i pełny scenariusz, wyszukuje i licencjonuje legalne obrazy, klipy wideo, muzykę/SFX i grafiki SVG, samodzielnie wybiera profesjonalną animację, typografię i wykresy/tabele, łączy je wspólną kamerą, dodaje dźwięk, waliduje rzeczywiste klatki, koryguje problemy, a następnie oddaje gotowy MP4 i raport wykorzystanych zasobów oraz danych.

**Dziś mamy fundament, nie gotowy produkt docelowy.** Kod posiada Creative Spec v1, Studio i Camera Canvas, podstawowe transformacje i animacje, `bars/donut/stats` i liczniki, moduły audio, wstępne wyszukiwanie zdjęć oraz Lucide/Heroicons. Brak w pełni autonomicznego, licencjonowanego brokera multimediów i muzyki, pełnego animowania tabel, wspólnego grafu dowolnych obiektów, zaawansowanego solvera i niezawodnego autokorygowania estetyki. Część dawnych statusów projektu opisuje historyczne prototypy i wymaga audytu. Repozytorium jest obecnie publiczne; przed importem poufnych materiałów klientów trzeba ustalić politykę bezpieczeństwa.

**Ważne:** plan zawiera 64 zadania: 44 pakiety `MD-*` oraz 20 pakietów `DM-*`. Status `fragmenty istnieją` nie oznacza wdrożenia ani odbioru. Nie wolno twierdzić, że każda animacja zawsze będzie profesjonalna wyłącznie na podstawie testów automatycznych; jakość wymaga testów i oceny człowieka.

## B. Jedna ścieżka produkcyjna i jeden render graph

```text
Brief użytkownika -> LLM (konkretna intencja, odbiorcy, styl i fakty)
   |
Creative Spec / Data Spec / Approved Brand Guidelines
   |
Capability Registry + validator (tylko faktycznie dostępne techniki)
   |
Creative Director + Data Director + Icon/Media Director + Audio Director
   |                        |                      |
Asset Broker (foto/wideo/SVG/audio/licencje)    Dane (CSV/JSON/XLSX, typy, jednostki)
   |                        |                      |
   +------------------------+----------------------+
                            |
Motion Plan (sceny, grafiki, wykresy i tabele, timing, camera, muzyka)
                            |
ONE Render Graph (obiekty, z-order, local/group/world/camera/viewport)
                            |
Layout Solver + keyframes + typografia + film + wykresy + maski + dźwięk
                            |
Real MP4 frames -> Quality Director -> ograniczona samonaprawa
                            |
Export + storyboard + rights/source/data ledger + ocena mobilna
```

**Architektoniczna reguła:** wykres, tabela, SVG, zdjęcie i wideo korzystają z **tych samych systemów czasowych, transformacji, maskowania, kamery, czytelności i walidacji**. Rodzaje komponentów są różne, ale nie wolno wprowadzać dla nich pięciu niespójnych rendererów.

**P0** = wymóg profesjonalnej bazy; **P1** = zaawansowana reżyseria i wyszukane animacje; **P2** = opcjonalny pełny 3D, GUI, duża skala. Przejście do kolejnego etapu wymaga dowodu, że kryterium odbioru poprzedniego jest spełnione; prace niezależne mogą być wykonywane równolegle.

## C. Jeden spójny backlog 64 zadań

**Statusy wstępne:** `fragmenty istnieją — zweryfikować` = kod częściowo istnieje, zakres zadania nie został dowiedziony; `do wdrożenia` = brak potwierdzenia zakończenia całości. Ukończenie zadania zawsze wymaga: kodu, testów, rzeczywistego MP4 lub testu odpowiedniego typu zasobu, kontroli praw/liczb, dokumentacji, akceptacji jakości tam, gdzie dotyczy.


### F0. Inwentaryzacja, wzorce i polityka jakości

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-001** | P0 | verified audit recorded; runtime paths remain multiple | Inventory existing modules, deprecated pipelines, media/license state and identify single runtime of record. Evidence: `docs/F0_AUDIT.md`; repository catalog reproduced at 30 items. | — |
| **MD-002** | P0 | partial; human-observation blocker | Establish 24-shot golden reference suite with human annotations and failure examples; store in golden manifests. Existing 18-item board has blank timecodes; do not invent annotations. | MD-001 |
| **MD-003** | P0 | implemented locally; tests pass | Build public CapabilityRegistry v2 incl icon packs, stock providers, audio, current feature flags and limitations. Evidence: `CapabilityRegistry` and CLI tests; provider search is not rights clearance. | MD-001 |
| **MD-004** | P0 | implemented locally; actual assets remain blocked | Establish licensed asset ID/provenance schema and default rights policy; block unreviewed footage/music. Unknown rights remain `delivery_ready: false`; do not infer clearance. | MD-001 |
| **MD-005** | P0 | reconciled locally; owner gates remain open | Reconcile docs/MASTER_PLAN.md, docs/ROADMAP_STATUS.json and source status, especially repository privacy and client licensing. Evidence: `docs/F0_AUDIT.md`; GitHub visibility is PUBLIC. | MD-001; MD-003 |

**Warunek odbioru F0:** Inwentaryzacja każdej rzeczywistej funkcji, zasady praw/licencji, zatwierdzony materiał referencyjny i brak sprzecznych statusów.

### F1. Autonomiczne banki mediów, SVG, muzyka i fundament danych

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-101** | P0 | search adapters + JSON-first `media-search` CLI implemented; live verified (Pexels/Pixabay/Wikimedia/Openverse) | Implement Pexels and Pixabay photos+videos API adapters, Unsplash compliant photo adapter, Wikimedia image/video/audio and Openverse image/audio (anonymous + optional OAuth) adapters. Mock and live searches verified; results remain candidates (`rights_status: unknown`). | MD-004 |
| **MD-102** | P0 | implemented locally + on main; `.env` loader + anonymous Openverse quotas wired | Provider-specific credentials/OAuth checks, local `.env` loader, default `User-Agent`, local quotas (incl. Openverse anonymous 20/min, 200/day), bounded retry/backoff, persistent private metadata cache (Pixabay TTL 24h), explicit Unsplash download tracking and exact-item review decision. | MD-101; MD-004 |
| **MD-103** | P0 | JSON-first `media-download` wired for image/video/audio; live quarantine download verified | Deterministic provider ranking/fallback; exact candidate provider/ID/source/download URL and target platform require human-reviewed decision before networking; host/IP/redirect allowlist, size/time bounds, atomic quarantine, checksum/FFprobe (incl. audio), explicit H.264/AAC transcode. | MD-102 |
| **MD-104** | P0 | implemented; all 5 icon packs + Material root-fill recoloring + Cairo fallback verified, mobile review pending | Implement icon packs Lucide/Heroicons/Tabler/Phosphor/Material with pinning, safe SVG, root-fill inheritance for fillless paths, macOS Homebrew Cairo fallback, semantic selection, cache and legal notices. 30 live upstream icons rendered in a synthetic 1080x1920 test MP4; Studio export records source/version/license/hash in `docs/evidence/md104-icon-pack-smoke.json`. | MD-003; MD-004 |
| **MD-105** | P0 | partial; Commons + anonymous/OAuth Openverse audio search (`--kind audio`) and FFprobe quarantine download wired | Wikimedia Commons/Openverse audio metadata search and generic FFprobe-verified audio quarantine download are wired; Pixabay 403 emits Cloudflare workaround guidance. Search results remain rights-unknown and acquisition requires exact reviewer/source/download URL, attribution, license and platform. Curated cross-platform-safe packs, authorized automated selection, mixes and human playback/legal review remain incomplete. | MD-004; MD-102 |
| **MD-106** | P0 | mock suite passes; opt-in live search/download harness verified with Wikimedia/Pexels/Pixabay/Openverse | Provider mock tests cover failures, ranking, rights binding and quarantine acquisition. `tests/test_media_live_optin.py` offers environment-gated live search and exact-item reviewed download into a temporary quarantine; skipped by default in CI. | MD-103; MD-104; MD-105 |
| **DM-001** | P0 | local file loader implemented; connector integration pending | Typed data source loader for CSV/JSON/XLSX and authorized connector exports; schema/number/locale/rights provenance. Synthetic CSV/JSON tests pass; XLSX requires optional extra; no client data imported. | MD-004 |
| **DM-002** | P0 | implemented locally; synthetic tests pass | Data Integrity Validator, calculation ledger, deterministic Decimal aggregation, named rounding and explicit units/currency/period; nulls, unauthorized provenance and invalid denominators fail closed. No client data imported. | DM-001 |
| **DM-003** | P0 | partial; unified `compile_visualization_scene` for `line`, `bar`, `stacked_bar` and `table` | Data Director plans explainable families; `compile_visualization_scene` (`line_chart_scene`, `bar_chart_scene`, `stacked_bars_100_scene`, `table_scene`) compiles validated `LoadedData` + `VisualizationPlan` into typed Studio scenes with exact-value provenance. | DM-002; MD-003 |

**Warunek odbioru F1:** Legalne wyszukanie/pobranie zdjęcia, wideo, ikony i audio z pełną proweniencją; import i walidacja liczb oraz wybór rodzaju wizualizacji.

### F2. Jedna architektura scen i bezpieczeństwo geometrii

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-201** | P0 | additive typed boundary implemented locally; legacy parity tests pass | Typed Creative Intent -> Motion Plan -> Render Graph. New stages snapshot/validate Creative Spec v1 and convert deterministically back to the existing Studio/Camera Canvas manifest contracts; no shared graph/migration claim. | MD-003; DM-002 |
| **MD-202** | P0 | partial; Studio Node trees and Camera Canvas shots share `TransformHierarchy` / `Affine2D` | Common hierarchy for 2D/video/vector/text/camera; reconcile Studio and Camera Canvas. `build_transform_hierarchy` (Studio) and `build_camera_canvas_hierarchy` + `camera_world_to_viewport` (Camera Canvas) use the shared `TransformHierarchy` / `Affine2D` contract. | MD-201 |
| **MD-203** | P0 | partial; sampled Studio QA checks FreeType ink bboxes + platform safe polygons | Actual glyph shaping, text fit, multi-line wrap, mask bounds and platform safe polygons (`platform_safe_polygon` incl. 6-vertex L-polygons for Reels/TikTok/Shorts action rails). | MD-202 |
| **MD-204** | P0 | partial; `plan_camera_path` + `audit_camera_canvas` verify travel, rotation bounds and subject retention | Camera path planning, arbitrary positions, controlled rotation and subject retention (`plan_camera_path` measures settled and in-flight subject viewport retention and flags excessive rotation). | MD-202; MD-203 |
| **MD-205** | P0 | partial; `solve_scene_layout` builds real candidate scenes and hard-rejects timeline QA violations | Layout candidate generator, hard-reject invalid placements (`_safe_area`, `_collisions`, `_text_ink_safe_area` across sampled frames), soft artistic scoring and explainable choice (`solve_scene_layout`). | MD-203; MD-204; DM-003 |
| **MD-206** | P0 | partial; Studio QA samples track keyframes, analytical easing extrema (`back`/`spring`) and interval probes + `audit_camera_canvas` | Transform- and timeline-sampled QA at every keyframe extremum (`easing_extrema_progress` for `back`/`spring`) and representative in-between frames (`sample_geometry_frames`, `audit_camera_canvas`, `tests/test_qa_timeline_sampling.py`). | MD-205 |

**Warunek odbioru F2:** Wspólny graf, typografia, kamera i algorytm kadrowania nie ucinają czytelnych elementów w klatkach pośrednich.

### F3. Zaawansowany motion design ORAZ animowane wykresy i tabele

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-301** | P0 | partial; 8 distinct renderer-backed text mechanism families (`TEXT_MECHANISM_FAMILIES`) | Implement at least 8 genuinely distinct text mechanism families (`vertical-drift`, `curtain-mask`, `horizontal-wipe`, `lateral-slide`, `elastic-scale`, `optical-tracking`, `stagger-cascade`, `depth-focus`) with purpose and variation control (`select_text_mechanism`). | MD-202; MD-203 |
| **MD-302** | P0 | partial; grouped timing/easing curves and quiet-hold choreography; reusable typed-search field, staged icon entry, smooth explicit transition easing and hard-cut defaults implemented; new interaction visual review pending | Implement grouped timing/easing curves and semantic text hierarchy with quiet holds (`plan_choreography` + `TEXT_MECHANISM_FAMILIES`). | MD-301 |
| **MD-303** | P0 | partial; arc-length vector path/line trim (`trim_polyline`) and `animate_icon_state` implemented | Native SVG/vector path/trim (`progress`/`trim_start` on `line` and `path` nodes) and icon state change animations (`animate_icon_state`). | MD-104; MD-202 |
| **MD-304** | P0 | partial; `video_node`, `load_video_frame`, `crop_region`, `apply_shape_mask` and dynamic per-frame Camera Canvas video decoding verified with time-varying MP4 | Native video layer in Camera Canvas (`_tile(..., playback_time=time)`) and Studio (`video_node` / `video_layer`), real trim (`trim_start`/`trim_end`), masks (`rect`/`rounded`/`circle`/`pill`) and normalized crop (`crop_region`). | MD-103; MD-202 |
| **MD-305** | P0 | partial; `verify_shared_element_continuity` checks cross-scene object anchor continuity | Motion-blur/overscan improvements and shared-element transitions with real object continuity (`verify_shared_element_continuity`). | MD-204; MD-304 |
| **MD-306** | P0 | partial; `run_polish_typography_regression` passes 32 combinations (8 families × 4 aspects), human demo approval pending | Polish typography regression (`run_polish_typography_regression`), cross-aspect ratio checks (`9:16`, `4:5`, `1:1`, `16:9`) and multi-family demo verification. | MD-203; MD-301; MD-303; MD-304 |
| **DM-004** | P0 | partial; vector line, ordered bars and 100% stacked bars + `bar_chart_scene` / `stacked_bars_100_scene` bridges | Studio renders explicit-domain line charts, ordered bars (`stable_row_id`) and 100%-normalized vector stacks; typed `LoadedData` bridges preserve source hash and exact values. | DM-003; MD-202; MD-203 |
| **DM-005** | P0 | partial; stable-ID table scene + `sorted_table_scene` + `paginate_table_scenes` | Table renderer supports explicit row IDs, deterministic sorting (`sorted_table_scene`), lossless multi-scene pagination (`paginate_table_scenes`), ordered columns, width weights and alignments. | DM-001; MD-203 |
| **DM-006** | P0 | partial; animated table row reorder (`dy` track), row/cell highlights, cell value counters and bar/line progress | Semantic animation choreography: bar grow, polyline trace, animated row reorder (`animate_from_row_ids`), row/cell highlights (`highlight_rows`/`highlight_cells`), and cell number replacement (`cell_transitions`). | DM-004; DM-005; MD-302 |
| **DM-007** | P0 | partial; `audit_data_scene` checks mobile font floor, non-truncation and reading hold | Camera-safe chart/table placement, real glyph bounding boxes, contrast QA, collision, mobile text-size floor and reading hold tests (`audit_data_scene` wired into Studio QA). | DM-005; MD-205; MD-206 |

**Warunek odbioru F3:** W jednym rendererze działają różnorodne animacje tekstu, rzeczywiste wideo, wektory SVG, czytelne tabele, wykresy i liczniki.

### F4. Audio, social media, samonaprawa i odbiór P0

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-401** | P0 | partial; `select_compatible_audio` filters/ranks legal cross-platform audio fail-closed | Autoselect legal cross-platform audio; music and SFX compatibility filtering (`select_compatible_audio` enforces `rights_status=='approved'` and `delivery_ready`). | MD-105 |
| **MD-402** | P0 | partial; `plan_beat_cue_mix` builds beat grid, 3-bus gain staging, sidechain ducking envelopes and loudness QC | Beat/onset/cue model for animation/VO/SFX, bus mixing, ducking, loudness QC (`plan_beat_cue_mix`). | MD-401; MD-302 |
| **MD-403** | P0 | partial; `PLATFORM_PROFILES` + `platform_safe_polygon` (6-vertex L-polygons for Reels/TikTok/Shorts) | Platform profile registry (`resolve_platform_profile`), safe-zone polygons (`platform_safe_polygon`), captions/subtitles and locale adjustments. | MD-203 |
| **MD-404** | P0 | partial; `repair_scene_layout` runs bounded deterministic QA repair loop with audit trail | Frame-based quality repair loop, deterministic rerender, limited retries, audit report (`repair_scene_layout`). | MD-206; DM-007; MD-402 |
| **MD-405** | P0 | partial; `render_master_format_matrix` renders and probes portrait/square/landscape MP4s with per-format QA | Full HD 1080x1920 30fps master + review/square/landscape and audio validation (`render_master_format_matrix`). | MD-403; MD-404 |
| **DM-008** | P0 | partial; `credible_data_story_examples` provides 4 original benchmark datasets + scenes passing QA, human sign-off pending | 4 credible example videos with original datasets (`pv_generation_annual`, `household_storage_finance`, `regional_oze_share`, `campaign_conversion_lookup` in `credible_data_story_examples`); human art-director sign-off pending. | DM-006; DM-007; MD-403 |
| **MD-406** | P0 | partial; `run_end_to_end_delivery(..., render=True)` renders and probes multi-scene H.264 MP4 + provenance ledger in a fresh workspace | End-to-end brief->assets->render->rights/quality review->deliver runner (`run_end_to_end_delivery` verified with `render=True`). | MD-106; MD-405; MD-404; DM-008 |

**Warunek odbioru F4:** Brief -> legalne media i dane -> animacja -> audio -> MP4 -> QA -> telefon; wymagane demo wyników kampanii, finansów i OZE.

### F5. Reżyseria P1: 2.5D, morfing, Data Storytelling

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-501** | P1 | partial; `parallax_25d_group` builds multi-plane depth-weighted `dx`/`dy`/`scale` parallax | Photo/subject segmentation and consistent 2.5D parallax (`parallax_25d_group`). | MD-304; MD-203 |
| **MD-502** | P1 | partial; `character_accent_group` builds per-character staggered kinetic nodes with bounded tilt | Character geometry/tracking/morph, variable fonts, per-character 3D only as meaningful accent (`character_accent_group`). | MD-301; MD-203 |
| **MD-503** | P1 | partial; `morph_polyline` and `animate_along_path` implement vertex morphing and path-tracked motion | Rich SVG shapes/morph (`morph_polyline`) and tracked object animation (`animate_along_path`). | MD-303 |
| **MD-504** | P1 | partial; `bezier_camera_point` and `apply_camera_motion_blur` implement cubic-Bezier trajectory and velocity blur | Bézier camera travel (`bezier_camera_point`), speed profile control, focal anchor interpolation and spatial motion blur (`apply_camera_motion_blur`). | MD-204; MD-305 |
| **MD-505** | P1 | partial; `match_reference_rhythm` scores shot cadence against reference-board pacing profiles | Larger layout style library + stronger rhythm/style reference matching (`match_reference_rhythm`). | MD-002; MD-205 |
| **MD-506** | P1 | partial; `rank_video_sources` ranks clean-source footage by resolution, FPS and motion stability | Video motion matching and source quality ranking (`rank_video_sources`). | MD-103; MD-304 |
| **MD-507** | P1 | partial; `plan_audio_dramaturgy` plans hook/build/climax/resolve energy curve without over-synchronization | Multi-scene audio dramaturgy and adaptive timing without over-synchronization (`plan_audio_dramaturgy`). | MD-402 |
| **MD-508** | P1 | partial; `generate_and_select_storyboard` renders contact-sheet frames for 3 storyboard candidates and scores QA + pixel contrast + rhythm | Creative Director renders 3 different storyboard candidates and chooses with measurable evidence (`generate_and_select_storyboard`). | MD-505; MD-205 |
| **MD-509** | P1 | partial; `PreferenceLibrary` stores and recommends preferences gated on licensed/authorized reference provenance | Human-feedback preference library and template learning only with authorized/licensed reference assets (`PreferenceLibrary`). | MD-508 |
| **MD-510** | P1 | partial; `apply_natural_language_revision` compiles NL edits while preserving shot IDs and reporting cache-valid shots | Support natural-language revisions with stable shot identity and partial render caching (`apply_natural_language_revision`). | MD-201; MD-404 |
| **DM-101** | P1 | partial; `table_to_bars_scenes` compiles paired table -> bar scenes with shared `stable_row_id` and exact Decimal sum conservation | table -> chart transformation with shared object IDs and conservation checks (`table_to_bars_scenes` + `verify_shared_element_continuity`). | DM-005; DM-004; MD-202 |
| **DM-102** | P1 | partial; `build_waterfall`, `build_diverging_bar`, `build_bullet`, `build_heatmap`, `build_scatter`, `build_funnel` implemented in Studio | waterfall, diverging/slope, bullet, heatmap, scatter and funnel (`components/scenes.py`). | DM-004; DM-007 |
| **DM-103** | P1 | partial; `build_sankey` renders total-conserving source->target flow links with animated progress | Sankey/energy flows + animated process paths, total-conserving links (`build_sankey`). | DM-001; DM-004 |
| **DM-104** | P1 | partial; `morph_chart_scenes` + Studio `build_chart_morph` render smooth object-level position/width/counter morphs to MP4 | chart scene morphs preserving marks/scales and staged axis transitions (`morph_chart_scenes` + `build_chart_morph`). | DM-101; MD-305 |
| **DM-105** | P1 | partial; `DOMAIN_PRESETS` and `resolve_domain_preset` cover `pv`, `finances`, `marketing`, `operations`, `sales` | domain-aware presets for PV, finances, marketing, operations and sales (`resolve_domain_preset`). | DM-003; DM-102; DM-103 |
| **DM-106** | P1 | partial; `plan_data_narration_cues` links verified dataset peaks/troughs to narration cues and camera focus | data-aware narration/audio cue planning and camera choreography (`plan_data_narration_cues`). | DM-006; MD-402 |
| **DM-107** | P1 | partial; `select_data_story_variant` evaluates up to 3 visual variants across portrait/square/landscape | automatic three-way choice of visual storytelling variants; responsive animated layouts (`select_data_story_variant`). | DM-104; MD-508 |
| **DM-108** | P1 | partial; regression suite exercises all 11 Studio data-motion chart/table types (`test_data_renderer.py`), human golden sign-off pending | full regression suite across all 10+ types of data-motion scenes (`line_chart`, `bars`, `stacked_bars_100`, `table`, `waterfall`, `diverging_bar`, `bullet`, `heatmap`, `scatter`, `funnel`, `sankey`). | DM-101; DM-102; DM-103; DM-104; DM-105; DM-106; DM-107 |

**Warunek odbioru F5:** Zaawansowane filmy i animacje tabel→wykresów, heatmap, waterfall, Sankey i przepływów energii zachowują dane i są ocenione wizualnie.

### F6. Opcjonalne 3D, tracking, edytor, GPU i live data

| ID | Priorytet | Stan | Zadanie | Wymagane wcześniej |
|---|---|---|---|---|
| **MD-601** | P2 | partial; `render_3d_product_frame` + `build_product_3d` perspective-project `.obj`/prism meshes with 3-point Phong lighting | Real 3D/Blender product scenes and camera lighting, not simulated planar rotations (`validate_3d_product_scene`, `render_3d_product_frame`, `build_product_3d`). | MD-202 |
| **MD-602** | P2 | partial; `composite_depth_layers` performs per-pixel Z-depth DoF blur, parallax shift and tracked-badge occlusion | Depth maps / object tracking / compositing, advanced relighting only with approved models (`validate_depth_composite`, `composite_depth_layers`). | MD-501; MD-601 |
| **MD-603** | P2 | partial; `write_scene_graph_inspector_html` generates an interactive HTML5/SVG motion-path editor and scene tree inspector | Editable motion path GUI and scene graph visualization (`export_scene_graph_inspector`, `write_scene_graph_inspector_html`). | MD-201; MD-510 |
| **MD-604** | P2 | partial; `write_review_portal_html` generates an interactive HTML5 A/B comparison slider and shot-comment approval portal | Collaboration/approval portal, comparison slider, shot comments and release history (`build_review_portal_bundle`, `write_review_portal_html`). | MD-405; MD-510 |
| **MD-605** | P2 | partial; `execute_render_farm_batch` probes hardware H.264 encoders and executes batch MP4 jobs with shared warm segment caching | Cost-aware GPU render farm and brand-domain style optimization (`plan_render_farm_batch`, `execute_render_farm_batch`, `detect_hardware_h264_encoder`). | MD-406 |
| **DM-201** | P2 | partial; `snapshot_dataset_version` and `diff_dataset_snapshots` provide SHA-256 audit trails and historical diffs | scheduled live data snapshots with audit trail and historical comparisons (`snapshot_dataset_version`, `diff_dataset_snapshots`). | DM-001; DM-002 |
| **DM-202** | P2 | partial; `add_uncertainty_band` validates and attaches confidence intervals to time-series charts | advanced statistical/uncertainty animation and geographic maps (`add_uncertainty_band`). | DM-102; DM-103 |
| **DM-203** | P2 | partial; `annotate_chart_scene` attaches validated callout/threshold annotations and focus targets | editable dashboard/storyboard GUI; custom data annotations and user-directed focus (`annotate_chart_scene`). | DM-108; MD-603 |
| **DM-204** | P2 | partial; `validate_3d_data_justification` rejects 3D bar/pie/line gimmicks and requires 3 spatial axes + rationale | truly spatial 3D data scenes only if they improve comprehension (`validate_3d_data_justification`). | MD-601; DM-103 |

**Warunek odbioru F6:** Opcjonalne funkcje nie psują zatwierdzonych filmów bazowych i wykazują mierzalny wzrost jakości lub wydajności.

## D. Definicja ukończenia i bramki wydania

**Dla każdego zadania:** (1) test jednostkowy + integracyjny; (2) aktualny `Creative Spec` i prawdziwy `Capability Registry`; (3) przykład pełnego renderu, ew. sceny z rzeczywistymi klatkami; (4) sprawdzenie telefonu i rzeczywistych safe zones; (5) pełna identyfikacja użytych licencji i źródeł danych; (6) brak regresji w zatwierdzonych referencjach; (7) akceptacja człowieka, jeżeli dotyczy jakości wizualnej. Obszary bez plików audio/wideo mają odpowiednie dowody dla swojego typu, np. import tabeli, SVG lub licencji.

**Wydanie P0:** minimum 24 filmy referencyjne, 3 marki, 6 stylów, w tym minimum 4 wiarygodne animowane filmy oparte na **prawdziwych danych i tabelach**. W każdym: czytelna hierarchia, rzeczywiście różne mechanizmy ruchu, brak niezamierzonych ucięć i migania, spójny dźwięk, prawa do wszystkich mediów. Dane liczbowe — 100% poprawnych końcowych wartości oraz jednostek, jawne osie, sumy i okresy. Pełne profile 9:16, 4:5, 1:1 i 16:9, przetestowane w rozmiarze mobilnym. Żadne niezweryfikowane prawa muzyczne nie przechodzą bramki eksportu.

**Kontrola jakości:** 0 błędów blokujących geometrię, źródła, licencje i dane; przyjęta przez autora referencji oraz co najmniej jednego recenzenta dynamika, timing, kolor, optyczna hierarchia, dźwięk i oddziaływanie przekazu. Błędy wymagają korekty z limitem prób i ponownym sprawdzeniem (nie nieskończonego retry).

**Miary produktu:** pass-rate generacji, first-pass creative acceptance, koszt/minutę 1080p, powtarzalność, wykryte błędy klatek i danych, skuteczność legalnego wyszukiwania, cache hit ratio, liczba potrzebnych korekt, testy A/B człowieka. Bez ustalonej metody i bazy nie deklarować procentowego postępu.

## E. Szczegółowa specyfikacja motion design / SVG / media / audio / social

Poniższe sekcje są zachowanymi, szczegółowymi wymaganiami technicznymi wcześniejszego roadmapu, włączonymi w **ten sam dokument**. Oznaczają wymagania docelowe, nie stan wdrożenia.

### Product goal and definition of professional quality

Natural-language brief -> truthful storyboard -> autonomous rights-cleared media search -> art direction -> editable Creative Spec -> shot-level scene graph -> synchronised camera/typography/vector/video/audio -> real render -> visual/technical/licensing QA -> automatic correction where safe -> delivery for Reels, TikTok, Shorts and other placements.

The aim is consistently professional output, not a guarantee that every automatically generated video is artistically perfect. The system must reject under-specified, unlicensed or defective results instead of delivering bad clips and reporting success.

Quality pillars: narrative clarity, intentional variety, composition and hierarchy, legibility on phones, authored animation curves, appropriate footage, sound design, verified usage rights, brand consistency, export compliance and operational reliability.

### Evidence-based current baseline

Current source contains a working Creative Spec v1 interpreter and CLI; Studio scene renderer with H.264; motionkit/keyframes; camera_canvas for one persistent world with irregular camera stops; transition engine; text typesetter; composition candidate scoring; audio mux/QA; storyboard and frame-based tests; version-pinned Lucide and Heroicons SVG support; preliminary Pexels/Pixabay/Unsplash PHOTO search adapters.

Limitations verified from source:
- Stock adapters return metadata/URLs for photos; there is no unified, fully autonomous and licensed photo/video/music/SFX acquisition and selection pipeline.
- Camera Canvas uses a CPU Pillow world and four fixed compositional arrangements; no Bézier director path, focal-object-aware clipping guarantee, full 2.5D depth or native video layers in that mode.
- The Creative Director scores deterministic heuristics, not rendered-world perceptual or artistic quality.
- Camera typography currently has a small family set; no world-class semantic glyph morphology, full kinetic paths, per-character 3D, variable font trajectories or professional shared-element typography across shots.
- Icon library covers Lucide 0.468.0 (ISC plus some MIT-derived glyphs) and Heroicons v2.2.0 (MIT). No common provider registry for additional SVG/icon/illustration packs, asset-level licenses or semantics.
- Existing QA contains geometry and timing checks but cannot ensure all intermediate-frame camera-safe geometry, subject-aware cropping, intentional rhythm, good photography or aesthetic approval.
- Large portions of prior docs/ROADMAP_STATUS.json and docs/MASTER_PLAN.md describe older milestones and are stale. Reconcile status documents; do not treat checked historical gates as proof of current flagship artistic approval.
- GitHub repository is currently PUBLIC; decide whether private source/media is a project requirement before storing client material.

The plan below supersedes the old creative feature backlog for new work. Keep old assets and client deliveries until inventoried; the user allows retiring obsolete project formats, not accidental destruction of real source media.

### Motion design standard: mandatory director principles

Use animation principles from Adobe/Disney, temporal continuity, professional typography and Google's meaningful motion guidance. Explicitly model:
1. Staging: one clear visual idea and focal point per beat.
2. Hierarchy: dominant headline/subject; supports never compete.
3. Anticipation when it clarifies an impact; no mandatory fake bounces.
4. Ease-in/out plus separate speed/value curves; velocity and acceleration continuity at joins.
5. Follow-through / overlap proportionate to mass and material, not robotic synchronized stops.
6. Arcs, direction and pivots motivated by objects, not random motion.
7. Secondary action subordinate to the primary message.
8. Timing and spacing governed by distance, movement mass, phrase duration, VO and soundtrack.
9. Contrast of quiet holds and emphatic changes; breathing room for reading.
10. Continuity of objects, color, subject, movement direction and motivated scene transitions.
11. Restraint: no gratuitous bars, dots, abstract gradients, generic sparkles, every-word bouncing or arbitrary 360-degree spins.
12. Safety: avoid strobing/flashing patterns, unreadable moving glyphs and excessive large-field rotation.
13. Mobile reading: optical rather than nominal alignment; platform UI safe areas and caption clashes.
14. Honest storytelling: no invented numbers, fictitious brand endorsements, or assets falsely represented as the user's own projects.

These are evaluation rules, not automatic aesthetic certifications.

### Families of animation to implement

#### 3.1 Kinetic typography (P0–P1)
- Phrase-level masked reveals with baseline-safe glyph masks.
- Character-/word-/line-level stagger, independent timing and variable selector curves.
- Character convergence, tracking and kerning expansion/settle.
- Word substitution, tracked slot replacement, inline reflow and layout-resolving text shifts.
- Per-word scale/rotation/skew/opacity/blur with scene-relative semantic reasons.
- Variable font axes (wght, wdth, slnt) with licensed font support and coherent shapes.
- Text on path, kinetic punctuation, counters with units and truthful data ticks.
- Shared text-object continuity across transitions and camera stops.
- Photo/text occlusion via segmentation and z-order; typographic image masks.
- Depth-motivated 2.5D text, perspective (only if legible), collision-safe exit trajectories.
- Distinct family choice across nearby scenes; repeated patterns permitted when artistically motivated.
- Full HarfBuzz/FreeType glyph layout, Polish diacritics, font fallback, actual bounding boxes at every interpolated frame.
- Typography data model: semantic groups, animated properties, mask regions, pivots, hold/readability windows, mobile fallbacks.

#### 3.2 Shape and vector motion (P0–P1)
- SVG paths, Bézier path animation, draw-on/draw-off strokes, dash offsets.
- Topology-compatible shape morphs; else safe crossfade rather than broken interpolation.
- Nested groups, pivots, per-layer transforms, fills, gradients only when artistically warranted.
- Trim paths, organic reveal, path followers, icon state changes, reusable diagrams and process illustrations.
- Scene-graph vector geometry; native vector until raster output rather than low-resolution pre-rendered icons.
- Import sanitized SVG; disallow scripts/external resources/XXE/embedded remote assets.

#### 3.3 Photo/video, composites and postproduction (P0–P2)
- Keyframe crop, pan, Ken Burns, push/pull, perspective-aligned photo cards and match-cut.
- Subject-aware crop based on face/object/saliency; maintain visibility at all frame times.
- Masked foreground subject, simple background removal, depth-layer parallax, selective motion blur.
- Real stock video clip decode, frame-accurate trim, loop handling, FPS conversion, video-as-texture and PIP composition.
- In-scene tracked placements and video masks; transitions preserving object identity.
- Optional color grading and filmic noise restrained and brand-dependent.
- Procedural motion graphics: lines, ribbons, grids, shape trails, particles; no default decorative noise.

#### 3.4 Camera and space (P0–P2)
- Shared infinite editorial canvas with arbitrary non-grid shot centers and angles.
- Continuous cubic Bézier camera trajectories with per-segment angle unwrap, zoom and pivot/target curves.
- Distinct stages: approach, settle, reveal, hold, prepare exit.
- Camera-target constraints, scene crop polygon intersection and rotated text outline safety.
- Conditional adaptive overscan/zoom adjustment and dynamic layout repair.
- 2.5D depth-aware z-layers, parallax and occlusion, with camera collision/blur protection.
- Optional Blender/3D renderer for genuine spatial shots, products, lighting and reflections; never fake 3D with arbitrary spins as default.

#### 3.5 Transitions and editing (P1)
- Hard cuts, audio J/L cuts, motivated wipes and reveals.
- Whip pans, camera carryover, match move, zoom-through, photo-to-type shared element, mask takeover.
- Subject- and motion-vector-aware matching across clips; avoid random pixel dissolve as default.
- Animated data visualization is a **first-class Data Motion & Infographics Engine** and an explicit **P0 workstream**, not a small transition preset. See [DATA_MOTION_DESIGN.md](DATA_MOTION_DESIGN.md). Start with accurate chart/table primitives, mobile readability and exact data lineage; then extend to line/bar/donut/waterfall, heatmaps, rankings, Sankey, table sorting, chart-to-table morphs, progressive disclosure and beat-aware data storytelling.
- Optical interpolation optional; do not invent motion frames on product photos or introduce distortions silently.

### Style system / art direction catalog (P0)

Establish 8–10 style families with tokens and reference footage:
- Editorial premium / Swiss typography: restrained color, asymmetry, scale/negative space.
- Contemporary kinetic advertising: strong claim hierarchy and controlled dynamic timing.
- Documentary / cinematic: photographic storytelling, slower moves, motivated reveal.
- Product minimal / luxury: light, detail, softness, no needless gradient decoration.
- Social-native/UGC: recognisable narrative, human presence where relevant, subtitles.
- Tech/data storytelling: evidence-led diagrams, calibrated iconography.
- Playful/organic: carefully used elastic timing, illustration and secondary motion.
- Mixed-media/collage: torn edges, cut-outs, layered editorial placement, intentional paper grain.
- Optional premium 3D / isometric: only when footage and renderer capabilities support it.

Every style defines allowed fonts, sizes, line-height, palette, layout density, photo treatment, preferred motion families, easing, camera behaviour, audio motifs, forbidden effects, logo/CTA behaviour and budget of visual complexity.

Do not assemble style by random mixing. Build a reference library with verified visual examples, annotated motion moments, and rejection examples.

### Autonomous stock/asset acquisition (P0)

#### 5.1 Provider priority and legitimate APIs

PHOTO: Pexels (official photos API), Pixabay (official images API), Unsplash (official images API with hotlink/download tracking), Openverse (openly licensed images, item-level confirmation), Wikimedia Commons (API imageinfo/extmetadata per file).

VIDEO: Pexels Video API (current endpoint /v1/videos), Pixabay videos API, Wikimedia video where eligible. Add own footage and client-provided films. Mixkit and Coverr can be supported only through authorized/licensed integrations or manual import; do not assume a public search/download API.

SFX: prioritize a curated rights-verified internal CC0/commercial-safe library and original procedural Foley. Freesound API is available but commercial API usage needs provider permission/license. Openverse audio + Commons can supplement after item-level checking. Mixkit SFX license permits incorporation into commercial video but prohibits redistribution as a standalone asset library; use authorized import, not undocumented scraping.

MUSIC: curated, commercially cleared tracks under genuine cross-platform synchronization/use rights (CC0 or suitable CC BY with attribution, direct commercial licenses); search Openverse/Commons with original-source verification. Pixabay music requires checking Content ID risk and an authorized acquisition path; the documented Pixabay API primarily covers image/video, not a reliable public music/SFX download API. Do not assume Jamendo API commercial rights are free; it distinguishes paid commercial use. Meta Sound Collection and TikTok CML are placement/repertoire specific: never automatically export their restricted music for every other platform.

SYNTHETIC: generate simple original click, whoosh, riser, hit and transition sounds using local synthesis where suitable; store composition/reproducibility and verify loudness.

No scraping in violation of provider terms. No using free-as-in-gratis in place of license clearance.

#### 5.2 Multi-provider asset broker

New interfaces: ProviderAdapter.search, get_metadata, rights_check, download_authorized, rate_limit_status, explain_failure. Provider capabilities include media kind, authentication, returned rights, geographic limits, mandatory attribution and API download conditions.

Workflow per scene:
1. Derive keyword/synonyms from script, industry, region, mood, real object.
2. Search allowed APIs in parallel with cache, rate limits, timeout and retries.
3. Apply safe-search, topic consistency, commercial-use policy and optional people/brand-release filter.
4. Collect candidates: dimensions, length, orientation, freshness, tags, author, URL, license/version and evidence timestamp.
5. Rank by semantics, photographic quality, subject, negative space, crop retention, resolution, color continuity and duplication avoidance.
6. Download permitted variants only through compliant methods; hash, scan/validate, normalize and transcode.
7. Store per-media provenance and rights terms, photographer/credit obligations, platform permissions, change log and provider download event.
8. Fall back to another eligible source if rights cannot be verified; otherwise require user-supplied assets and refuse unsafe delivery.
9. Keep caches controlled and private; never resell providers' downloaded stock as a standalone catalog.

Asset manifest minimum: ID, type, original/source page, provider, creator, license ID/link/version, usage context, allowed platforms, attribution text, download date, expiry/revocation, model/property release uncertainty, content ID status, checksum, exact local derivative paths, transform recipe.

#### 5.3 Image/video intelligence

Vision embeddings for semantic fit, duplicate filtering and ranking; object/face/saliency masks; color harmony; empty-space estimation for text; object retention over a clip; reference-aware framing; 3–5 crop candidates; reject clipping/low resolution. Store subject masks and focal coordinates with provenance; user may override.

Video analysis: shot boundaries, usable in/out points, camera motion direction, face/subject stability, loudness, lighting, technical compression, resolution, frame rate and visual continuity. Match shot energy and direction to scene plan.

### SVG & icon library policy (MANDATORY, P0)

#### Approved initial providers and source-level conditions

- Lucide (ISC; some Feather-derived glyphs carry MIT notices) — default clean outline; current implementation exists, pinned 0.468.0.
- Heroicons (MIT) — outline/solid; current implementation exists, pinned v2.2.0.
- Tabler Icons (MIT) — large 24px-grid outline/filled catalog; add pinned local adapter.
- Phosphor Icons (MIT) — thin/light/regular/bold/fill/duotone; add style-weight-aware adapter.
- Google Material Symbols (Apache-2.0) — extensive configurable optical/fill/weight variants; add if visually appropriate.
- Iconify (MIT framework ONLY; icon packs have their own licenses) — use as discovery/metadata bridge, permit only audited icon sets.
- Simple Icons — brand logos only, with individual icon license/trademark verification; never infer universal clearance from project's CC0 notice.
- SVG Repo — mixed individual licenses; manual/provider-verified assets only; no blanket automatic approval.
- Remix Icon — switched to custom Remix Icon License v1.0 in January 2026; review precise terms and version before any import; do not treat all versions as Apache-2.0.
- OpenMoji (CC BY-SA 4.0) and other illustrated/icon packs — optional and license-gated; avoid generic emoji styling in premium brand reels.
- unDraw: free use in a film may be permitted, but its 2026 license restricts automated scraping/search/link/download integrations without permission; no autonomous provider integration by default.
- Storyset: free content requires attribution (or a suitable paid license); authorized manual ingestion, not unlicensed automatic scraping.

#### Icon design rules

Choose one primary icon family per brand/film; permit mixed libraries only with a proven optical equivalence and a documented reason. Normalize viewBox, optical sizing, baseline, caps/joins, stroke widths, corner radius, semantic size, monochrome palette, alpha and layer ordering. Default to a real, relevant symbol; zero icons is preferable to visual noise.

Meaning-driven icon selection: semantic tags/synonyms, pack availability, clarity at 9:16 phone scale, brand compatibility, no misleading symbols, no redundant icons beside obvious text. Preserve SVG vector paths as long as possible. Animate purposeful draw-on, trim, fill/outline state, turn, path following or topology-safe morph. Avoid perpetual spin, emoji-like clipart, random sparkles and decorative scatter.

Security/rights: pin package release, retain upstream license notices, validate per-symbol rights for mixed sets, sanitize SVG XML and references, block external loads/scripts/foreignObject/XXE, cap complexity/path count/file size, checksum downloaded source, make offline deterministic renders possible. Icon cache may include legal metadata but may not be redistributed in violation of upstream rules.

Implement IconRegistry with fields: pack/version/license/style/grid/stroke/weight, SVG source, provider URL, semantic tags, commercial allowed, attribution requirements, allowed transforms, hash, cached export. Provide an IconDirector returning explainable suggestions and 0–3 relevant icon candidates, never a hallucinated icon name.

Acceptance: import and render at least 25 representative SVGs across three packs; compare raster/rotated/animated frames at 1080p; no injected resources, clipping or inconsistent visual weight; track license notices in export provenance.

### Creative Engine / interpreter v2 (P0)

Separate Creative Intent from Motion Plan and technical Render Graph.

Creative Intent: narrative promise, audience, platform, brand, genre/style, scene purpose, time budget, facts, mandatory copy, approved media/rights, emotional energy.

Motion Plan: scene hierarchy and shot candidates, actual photos/video/icons/music IDs, layout constraints, choreography families, camera trajectory, synchronized sound cues, reading holds, transitions, rationale and alternative plans.

Render Graph: normalized coordinate spaces (world, group, camera, viewport), typed element/property tracks, easing, path/mask bounds, deterministic content-addressed asset IDs and frame-accurate timing.

Architecture:
- Capability registry advertises only executable versioned features and their restrictions.
- LLM emits constrained schema, not ad-hoc Python code; validate and compile with explicit errors.
- Director proposes 3 varied whole-film storyboard/animation plans, not 3 individually random layouts.
- Constraint solver rejects invalid layouts before choosing a favorite.
- Beat planner drives camera/media/typography from a common temporal rhythm.
- Explain why each animation and icon/photo was chosen.
- Versioned Creative Spec edits by scene ID and partial re-render cache.
- Content grounding: no invented client footage, statistics or music permissions.
- Risk-aware render gate: STOP or ask for approved alternatives if required data/rights cannot be established.

### Real layout solver + camera-safe geometry (P0)

Hard constraints at all critical and interpolated frames:
- All essential text glyph outlines (not only text rectangles) inside placement-specific safe polygons; check transformed bounds after rotation/skew/zoom/overshoot.
- Masks do not cut diacritics, ascenders or descenders.
- Foreground subjects and product logos remain visible across crop and camera travel.
- Text/image intersections intentional only; overlap is rejected when it harms legibility.
- Minimum touch? Not needed for rendered video. Instead optical spacing and visual readability at typical phone size.
- Balanced negative space, modular typographic baseline/grid and deliberate asymmetry.
- Camera stop centers and pivots guided by visual focal anchors, not only regular axes.
- Source image resolution sufficient for maximum zoom and selected crop.
- Strong contrast with real post-composited frame, not just configured color tokens.

Generate layout candidates with hard-reject filters + weighted, calibrated aesthetic scores; use crop/subject/semantic continuity costs; expand masks/overscan where needed; replan if nothing is safe.

### Audio Director (P0–P1)

Autonomous legal music and SFX search; classify genre, BPM, mood, instrument density, safe platforms, claims risk, license/attribution, duration and approved use.

Track analysis: beat/onset, phrase changes, quiet gaps, perceived energy and speech conflicts. Plan animation landmarks on relevant accents without forcing every entrance to a beat. Add Foley for camera whoosh, image shutter, contact/impact, UI action, ambient textures; avoid repetitive toy-like whooshes.

Sound graph: independent voice/music/ambience/SFX buses; crossfades, sidechain ducking, de-esser/limiter where justified; multi-platform loudness profiles based on measured reference and listening, not universal arbitrary LUFS. Validate clipping, true peak, start/end tails and unwanted silence. Record Content ID/licensing metadata. Provide intelligible captions with accurate timestamps and no overlap with UI safe zones.

### Social media deliverables (P0)

Profile registry per PLACEMENT, not generic 'vertical':
- IG/FB Reels, IG Stories, TikTok In-Feed, YouTube Shorts;
- optional Feed 4:5, square 1:1, horizontal 16:9 and 3:4 as requested.
- 1080×1920 9:16 H.264/AAC as baseline master; 30 fps, optional 60 fps for selected effects; preview 540×960 or 720×1280.
- Format-aware composition reflow, never simple cropping of the same 9:16 scene for every target.
- Source-of-truth UI overlays/safe-area templates per platform, ad placement, CTA and date; avoid hardcoded single percentage for all placements.
- Strong first-second hook, clear problem/benefit/proof/CTA as appropriate to campaign; visually appropriate human/product focus and honest brand claims.
- Subtitles and locale-specific text with optional exports without burned captions for platform-native subtitles.
- Validate output codec/resolution/frame count/pixel format/audio/channel, color space and true mobile readability.
- Verify cross-platform music rights separately when producing the same video for multiple destinations.

Platform references: Meta Reels business guide, TikTok business ad guide and safe-zone templates, Google/YouTube upload/ads specs. These change and must be refreshed by the provider profile module.

### Quality gates / self-repair (P0)

G0: Brief truth/facts/brand constraints.
G1: License/platform rights and asset provenance; strict no-go for missing permissions.
G2: Asset readiness (resolution, file health, color, video duration, source credibility).
G3: Storyboard narrative and motion variety.
G4: Constraint-based geometry at camera/typography extremes, after masks and post-compositing.
G5: Sound timing and mix; safe flashing/motion; dialogue and subtitles.
G6: Actual-frame/contact sheet/motion-strip analysis, not manifest-only.
G7: Export/codec/stream/metadata and device safe-zone verification.
G8: Review score with reasons; redo specific scenes, never conceal failure.
G9: Optional human approval before client paid ad publication.

Automated correction loop: detect -> classify -> select minimally invasive correction -> re-render only affected scenes -> compare before/after -> accept only if measurable improvement and no new regressions. Cap attempts, report unresolved warnings and offer alternatives. No infinite autonomous retries.

Golden set: at least 24 deliberately varied example reels, spanning 6 styles, different media types, 3+ brands, Polish diacritics, all platform targets and demanding edge cases. Human A/B reviews rate hierarchy, craftsmanship, rhythm, relevance and audio; technical success cannot pass this creative gate alone.

### Architecture, performance and operations (P0–P1)

- Normalize Studio, camera_canvas and media clip compositing onto one typed frame/timeline interface, rather than separate ad-hoc renderers.
- Introduce transform hierarchy (local -> group -> world -> camera -> viewport), property curves, transition boundaries, plus object IDs across scenes.
- Keep PIL/CPU renderer for regression/preview; evaluate Skia/GPU-based render or FFmpeg filter graph for final complex effects, profiling first.
- Adaptive supersampling, interpolation, subframe motion blur, color management, font shaping and deterministic alpha compositing.
- Streaming tiles and per-shot render caches rather than a single huge RGBA world; media memory and max 32MP world are current constraints.
- Separate asset fetch workers, layout analysis, render workers, export verification, and artifact storage; concurrency/rate budgets.
- Versioned immutable manifests, dependency locks, content hashes, audit logs, minimal privileges, no API keys in manifests or CI logs.
- Preserve source media outside Git for larger libraries; encrypted and backed-up object storage with rights/retention policy.
- Resolve repo visibility policy (public currently) before adding confidential client data.
- CI matrix for tests, 1080x1920 renders, CPU portability, Polish fonts, video/audio licenses, visual regressions and provider mocks.
- Older roadmap entries must be reconciled to truthful status; don't report completed features from local/unmerged prototypes.

## F. Szczegółowa specyfikacja Data Motion, wykresów i tabel

Włączona równorzędnie ze wszystkimi funkcjami motion design. Wersja Data Motion DSL poniżej jest **propozycją przyszłego schematu**, nie obecną obsługą Creative Spec v1.

### Business objective

Create reliable, high-end moving data stories for social video from factual numeric and tabular data. LLM supplies narrative questions and semantic intents. A Data Director chooses an appropriate visualization, Data Validator verifies the source and value rules, layout/animation engines render it across 9:16, 4:5, 1:1 and 16:9 formats; visual QA confirms mobile readability and semantic fidelity.

Sample scenarios: PV generation vs self-consumption, hourly heatmap of consumption, before/after bills, advertising campaign leads and CPL, CAC evolution, ROAS, conversion funnel, rankings by location, financial cash flow, comparisons of offers and process performance.

Today the source contains `build_bars`, `build_donut`, `build_stats`, and number/counter motion; these are **foundational limited layouts**. A full table renderer, automatic chart inference, data lineage, animated reshaping, data morphing, font-safe number motion and responsive progressive disclosure are **not yet equivalent fully implemented capabilities**. Never advertise them as available before tests.

### Data integrity is a hard invariant

- Data is immutable: each animated output frame derives from validated typed source and declared transforms; animation interpolation must never alter the final reported observation.
- Validate: source URL/file/title, import time, measurement period/timezone, data type, actual sample size/denominator, base year, currency, unit, missing/null, negative and zero, duplications, outliers, sorting and normalization, rounding, percentage sum, aggregation type, uncertainty when known.
- No arbitrary fabricated bars, comparisons or text. Do not infer causation from correlation or infer missing numbers from screen height or design metadata.
- For columns, bars and areas using length/area to represent a magnitude, appropriate proportional encoding and zero baseline are default. Lines representing change over time can use a nonzero axis only when it is clear and not misleading; keep truthful labels.
- Direct labels should show final exact rounded values and units. Counters interpolate visual numbers but converge precisely to the validated source values and never present intermediate frames as measured history.
- Preserve totals when transitioning table <-> chart, or pivoting categories; reject transitions that silently lose categories.
- Highlight denominator, category granularity, chart units, source and reference date. If numbers are estimates, mark them as estimates.
- Render percentages with explicit rounding policy and check data-bound percentages at final state.
- Preserve units and locales: Polish decimal comma, thousands spaces, PLN, zł, kWh, kWp, t CO2, %, p.p.; distinguish percentages from percentage-point changes.
- No invented business outcomes, unverified client ROAS/CAC, fictitious precise energy returns or graphs falsely implying source credibility.

### Visualization selection: question before chart type

Use editorial intent, dimensionality and domain. Categories follow FT Visual Vocabulary:

| Insight | Default forms | Alternatives | Notes |
|---|---|---|---|
| Magnitude / ranking | sorted horizontal bar | lollipop, dot plot | readable long labels, zero baseline for bar |
| Change over time | line chart | small multiples, columns | highlight changes/time endpoints |
| Deviation from target | diverging bar | bullet, slope | clear reference line |
| Part-to-whole | 100% stacked bar | donut for few sectors | avoid excessive tiny slices |
| Flow / conversion | funnel | Sankey for branching | preserve totals and missing branches |
| Distribution | histogram | dot/box | explain binning and spread |
| Correlation | scatterplot | bubble | no automatic causal claims |
| Matrix / time x category | heatmap | small multiples | clear continuous/discrete legends |
| Financial bridge | waterfall | running total line | signed values and cumulative audit |
| Multiple exact metrics | table | KPI cards, ranked comparison | table is best when exact lookup matters |
| Geographic differences | dot/bar by location | map when geospatial pattern relevant | appropriate rates for choropleths |
| Relationships / systems | flow, network diagram | annotated process | data versus illustrative diagram must be distinguished |

Chart selection requires an explainable record: audience question, chosen marks/encodings, rejected candidates, precision needs, source, domain and expected reading time.

### Animated data grammar — real mechanisms, not identical fades

#### 4.1 Bars and columns
- Axis and baseline first, then bar growth tied to validated value.
- Stagger categories by meaning, not automatically every bar.
- Sort/re-sort with stable object identity and smooth vertical reordering.
- Emphasize selected bar by color/opacity/callout, never misstate values by distortion.
- Stacked/100%-stacked bars animate portions while conserving totals.

#### 4.2 Lines and time series
- Draw-on via actual data points and line interpolation; preserve plotted geometry.
- Callout events and annotate peaks/troughs.
- Optional cursor or vertical tracker reveals exact historical sample at real timestamps.
- Animated comparison years/series with matching time scales; never fabricate in-between historical points unless visibly marked as mathematical interpolation.
- Reveal axis units/times and stable reading hold.

#### 4.3 Donut, pie and proportions
- Segment sweep starts from mathematically correct angular extent; labels track sectors without overlaps.
- Center value and total communicate real part-to-whole.
- Limit segments; prefer stacked bars for many categories; do not use perspective/3D pie distortion.
- Ensure value proportions sum with an explicit rounding strategy.

#### 4.4 KPI, counters and financial metrics
- Number ticker, digit-place choreography, count-up / count-down, rolling counter, delta reveal and before/after substitution.
- Correct units, p.p. versus %, currency, date period and source.
- Never count through physically nonsensical states if numerical sequence could be mistaken for source observations; visual-only counter marked as reveal.
- Strong hold after number settles.

#### 4.5 Tables / matrices (first-class objects)
- Typed table with column metadata, header groups, keys, sort, number format and semantic highlight.
- Auto-fit columns based on accurate font bounds and priority. Freeze/stick key dimensions logically in video; for a complex table use **progressive disclosure**, not tiny unreadable cells.
- Distinct effects: row reveal, column reveal, cell value-change, sort/reorder with stable ID, cross-highlight row/column, transform selected row into KPI or bar, filter categories, morph table -> chart -> table.
- Large tables: show only 3–7 semantically important rows per screen (calibrate to typography and duration); paginate/split into multiple beats preserving headers, scale and context. Original full data remains available as a report/CSV and is not dropped from source.
- Grid lines minimal, zebra pattern optional and subtle. Prefer right-aligned numeric values with tabular numerals; units consistently in heading.
- Never animate sort by replacing numbers independently of category identity; row objects must persist across state changes.
- Table row-to-chart morph maintains category/value mapping and signed values.

#### 4.6 Advanced
- Waterfall: build up/down from signed deltas with cumulative total check.
- Heatmap: reveal cells/row groups, stable legend and accessible perceptual color scale; show min/max and selective detail.
- Sankey: preserve flow conservation and label main pathways, show animated directional tracers without implying false dynamics.
- Scatter / bubble: preserve quantitative axes, rank by visual salience rather than arbitrary movement.
- Small multiples and dashboards: KPI reveal -> one main chart -> focused detail -> summary; never cram an entire desktop dashboard into a 9:16 frame.
- Animated maps only when rates, administrative boundaries and geography are accurate.
- Energy-specific diagrams: generation -> self-consumption -> storage -> grid; distinguish measured / estimated / simulation values and never depict physically impossible flows.

### Data Motion DSL: semantic descriptions, not manual drawing

Creative Spec v2 must accept reusable data references and visualization intent:

```json
{
  "data_sources": [
    {"id":"energy-2026","kind":"csv","path":"assets/energy-2026.csv","timezone":"Europe/Warsaw"}
  ],
  "shots": [{
    "id":"consumption-trend",
    "intent":"explain_growth",
    "headline":"Zużycie energii",
    "data_visualization":{
      "source":"energy-2026",
      "question":"How did consumption change by month?",
      "form":"auto",
      "dimensions":{"x":"month","y":"kwh"},
      "units":{"y":"kWh"},
      "focus":{"highlight":"last_observation"},
      "motion":{"family":"progressive_line_reveal","after_camera_arrival":true},
      "footnote":"Dane za 2026"
    }
  }]
}
```

This is a **proposed future schema**, not currently supported by the Creative Spec v1 compiler. Requirements: strict JSON Schema, version migration, explainable plan, internal typed source references, no arbitrary Python execution or expressions from untrusted LLM output.

Interpreted pipeline:

```text
CSV / XLSX / validated JSON / authorized Sheets / API
    -> Data Import + Types + Provenance + Calculation Engine
    -> Data Director: question -> chart/table/layout candidates
    -> Semantic Chart Model: categories / series / axes / values / units
    -> Motion Choreographer with stable IDs
    -> Camera-safe Responsive Scene Graph
    -> Exact Frame Renderer (SVG/vector/raster/video)
    -> Data Integrity + Mobile Legibility QA
    -> MP4 + source ledger / data appendix
```

### Rendering architecture

- Data Viz IR: `DataSource`, `DataFrameSnapshot`, `Field`, `Measure`, `Unit`, `Category`, `Scale`, `Axis`, `Mark`, `Legend`, `Annotation`, `Transition`.
- Static layout first, then animated numeric attributes. Frame `t` maps typed observations to visual primitives; golden frame equals valid terminal observation.
- Scene-wide coordinate transforms apply to entire chart/table groups. Text labels may be selectively camera-facing to remain legible.
- Chart marks have persistent IDs and are animated across sorted, filtered and reformatted states, not regenerated as unrelated objects.
- Where necessary, use segment-based animation: axis appears -> marks build -> callout -> hold -> exit. Avoid simultaneous data motion and camera rotation that prevents reading.
- Native SVG/Pillow/Skia/FFmpeg compositing can render chart primitives; D3/Observable Plot/Vega-Lite are useful references for chart selection/grammar and may be options for authoring, but don't require an always-on browser runtime in a Python renderer.
- Render full 1080x1920 quality and show real-screen previews.
- Precompute label widths and tick locations. Implement min label separation, annotation displacement, clipping masks, line simplification preserving significant events and collision checks.

### Visual/accessibility/mobile rules

- First impression: one claim, one primary chart, one highlighted finding.
- Progressive disclosure: more detail comes after audience knows what to look for.
- Prefer directly labeled elements over distant legends; legend only if needed.
- Numerals must be optically aligned, with consistent format and locale.
- Use color plus labels, position or symbols; don't rely on red/green alone.
- Critical chart marks should meet minimum non-text contrast where applicable, and text labels need text contrast; see WCAG 1.4.11 and 1.4.3.
- Avoid low-contrast hairlines, excessive gridlines, 3D bars/pies, misleading truncation, gratuitous pie slices and overly rapid animations.
- Short social content: visually progressive summaries beat full small-text dashboards.
- Chart hold at the end must accommodate a real reading interval, calculated from chart category and text count, not a fixed 0.6 seconds.
- Camera motion stops before detailed labels enter, unless motion is essential to the story.
- Legends/sources must be visible long enough to establish context; full citations additionally in export metadata/companion text where appropriate.

### Acceptance tests and golden showcase

Required datasets: positive/negative values, nulls, zero, duplicate keys, >100 rows, Polish decimals, nontrivial currency, percentages summing approximately/not exactly 100, denominator changes, unusual category widths, large and small scales, streaming/source changes and inaccurate input examples.

CI requirements:
- Values/totals remain invariant through interpolation, sorting and table/chart morph;
- No negative bar length for positive value, no sign inversion and no phantom point;
- 100% chart labels and key data within viewport/platform safe area at target frames;
- 100% verified unit/currency/percentage/period provenance; source shown or recorded;
- Color contrast checks on marks and text; color-blind-safe alternative encoding;
- Null/missing values visibly handled, not silently zero-filled;
- Mobile reading QA at true preview width and meaningful hold time;
- CI golden videos 9:16, 4:5, 1:1, 16:9 and Polish font regression;
- Video demo categories: marketing CPL by region; monthly revenue; PV/storage power flow; pre/post energy bill; table rank/reorder; table-to-chart morph; heatmap time-of-day; waterfall of costs; multi-year line; funnel conversion;
- Human review of narrative truth, aesthetics, legibility and motion coherence.

## G. Pierwsze kroki wykonawcze

1. **F0 / MD-001–005:** audyt prawdziwego stanu kodu i dokumentów, obecnych zależności, prywatności repo, katalogu efektów oraz referencji jakości.
2. **F1 / MD-101–106 równolegle z DM-001–003:** zbudować policy-gated broker mediów i ikon oraz typowany import liczb.
3. **F2 / MD-201–206:** jeden Scene/Render Graph i Layout Solver chroniący dowolnie obrócony tekst, zdjęcia, ikony, wykresy i tabele.
4. **F3 / MD-301–306 plus DM-004–007:** natywne SVG i wideo, 8 rodzin typografii, animowane tabele, wykresy, liczniki, wykresy liniowe i rankingi.
5. **F4 / MD-401–406 + DM-008:** automatyczny dobór legalnego dźwięku, platformy i jakość, kompletne testy MP4, odbiory ludzkie.
6. Po stabilnym P0: zaawansowane sceny danych, table-to-chart, Sankey, 2.5D, Bézier, selektywne 3D według priorytetów F5/F6.

**Reguła wycofywania starych formatów:** zgodność wsteczna nie jest wymaganiem użytkownika. Stary kod można usuwać po zinwentaryzowaniu i sprawdzeniu, że nie giną autorskie materiały, źródła, prawa i zatwierdzone filmy. Nie usuwać danych klientów bez upewnienia się, że są odzyskiwalne.

**Procedura prac:** małe zmiany z numerem MD/DM -> test -> prawdziwy MP4 -> zestaw klatek -> ocena mobilna -> dokumentacja -> kolejna zmiana. Status bieżący w `ROADMAP_STATUS.json` jako wykonywalny dziennik, **nie odrębny plan**.

## H. Zweryfikowane publiczne materiały źródłowe

### Motion, media, licencje, SVG i profile platform


Motion: https://www.adobe.com/creativecloud/animation/discover/principles-of-animation.html
https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html
https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/speed-between-keyframes/speed.html
https://m1.material.io/motion/duration-easing.html

Stock photos/videos: https://www.pexels.com/api/documentation/ ; https://www.pexels.com/legal-pages/license/ ; https://pixabay.com/api/docs/ ; https://pixabay.com/service/license-summary/ ; https://unsplash.com/documentation ; https://unsplash.com/api-terms ; https://docs.openverse.org/ ; https://www.mediawiki.org/wiki/API:Imageinfo

Rights/audio: https://freesound.org/docs/api/terms_of_use.html ; https://mixkit.co/license/modal/sfxFree/ ; https://www.tiktok.com/legal/page/global/commercial-music-library-user-terms/pl ; https://www.facebook.com/help/instagram/402084904469945 ; https://creativecommons.org/faq/index.html ; https://pixabay.com/service/faq/

Icons: https://github.com/lucide-icons/lucide/blob/main/LICENSE ; https://github.com/tailwindlabs/heroicons ; https://tabler.io/license ; https://github.com/phosphor-icons/core/blob/main/LICENSE ; https://developers.google.com/fonts/docs/material_symbols ; https://github.com/iconify/iconify ; https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md ; https://www.svgrepo.com/page/licensing ; https://github.com/Remix-Design/RemixIcon/issues/1069 ; https://undraw.co/license ; https://storyset.com/faqs

Platform: https://www.facebook.com/business/ads/facebook-instagram-reels-ads ; https://ads.tiktok.com/help/article/video-ads-specifications?lang=pl-PL ; https://support.google.com/youtube/answer/15424877 ; https://support.google.com/google-ads/answer/13547298

Technical: https://github.com/harfbuzz/harfbuzz ; https://librosa.org/doc/main/api/generated/librosa.beat.beat_track.html ; https://ffmpeg.org/ffmpeg-filters.html ; https://www.w3.org/WAI/WCAG22/Understanding/three-flashes.html ; https://tech.ebu.ch/publications/r128s2

### Data visualization i data storytelling


- FT Visual Vocabulary: https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md
- European Data Portal guide based on FT: https://data.europa.eu/apps/data-visualisation-guide/choosing-charts-the-message
- Datawrapper chart layout, annotations and mobile: https://www.datawrapper.de/academy/customizing-your-bar-chart
- Heer & Robertson, Animated Transitions in Statistical Data Graphics, IEEE TVCG (2007): https://idl.uw.edu/papers/animated-transitions
- WCAG 2.2 graphical objects non-text contrast: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast

---
**Jeden dokument, jeden backlog, jeden zestaw kryteriów odbioru.** Starsze plany `PRO_MOTION_ROADMAP_2026.md`, `DATA_MOTION_DESIGN.md`, `MASTER_PLAN_LEGACY_V1.md` pozostają wyłącznie kontekstem historycznym, nie definiują konkurencyjnych etapów.
