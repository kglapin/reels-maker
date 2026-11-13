# LEARNINGS — Staniszewska Nieruchomości

Zgromadzone uwagi właściciela projektu z iteracji klipów Stories (październik–listopad 2026).
Przed generowaniem kolejnych materiałów dla tej marki przeczytaj ten plik w całości.
Dotyczy głównie `projects/stories/` (oferty gruntowe) i `story-13-kredyt-hipoteczny`
(finansowanie), ale zasady stylu przenoszą się na inne formaty.

## 1. Teksty i copy

- Pisz naturalną, zwięzłą polszczyzną. Unikaj sztucznych, „marketingowych" fraz —
  właściciel wielokrotnie je odrzucał (np. „JASNY PLAN OD POCZĄTKU",
  „Nie musisz znać języka banków", „Każda sytuacja finansowa wygląda inaczej").
  Krótkie, konkretne zdania brzmią lepiej.
- **Nigdy nie pisz „netto" ani „brutto"** w tekstach na ekranie (decyzja właściciela).
- Ceny formułuj naturalnie, np. „działki od 90 000 zł" — nie sugeruj, że najniższa
  cena dotyczy droższej pozycji z oferty.
- Jeśli klip dotyczy kredytu hipotecznego, **w finale musi być dosłownie
  „kredycie hipotecznym"** — bez tego nie wiadomo, o jaki produkt chodzi.
- Zachowuj polskie znaki diakrytyczne; nie łam wyrazów.
- CTA: „Porozmawiajmy…", „Umów prezentację", telefon 502 180 180.

## 2. Ruch kamery i animacje — kluczowe preferencje

- **Przejścia między scenami**: `pixel-dissolve` („szachownica") odrzucony jako
  amatorski. Używany i zaakceptowany kierunek: `radial-reveal` (miękkie otwarcie
  z centrum). Dostępne alternatywy: `iris-close-open`, `whip-pan`, `spin-zoom`.
- **Perspektywa 3D**: właściciel chce wyraźny ruch kamery z kątami (yaw/pitch/zoom),
  nie statyczne płaskie sceny. Silnik ma tryby `settle`, `drift`, `push` i
  **`path`** (kluczowe klatki `{t, yaw, pitch, zoom, pan_x, pan_y}`, smoothstep).
- **Najważniejsza zasada z ostatniej iteracji**: gdy elementy pojawiają się
  sekwencyjnie (np. logotypy banków), **kamera ma podążać za aktualnie
  pokazywanym elementem i utrzymywać go blisko centrum kadru**. Szerokie,
  generyczne przesunięcia są niewystarczające — generuj klucze `path` z
  rzeczywistych współrzędnych elementów i ich timestampów pojawienia.
- **Fragmentacja wejść**: treść ma pojawiać się „po kawałku", nie cała naraz.
  Właściciel chce animację **na poziomie pojedynczych słów**, nie linii czy
  zdań: `split_lines: "words"` (jeden węzeł na słowo, własny onset, układ
  końcowy identyczny). `cues` rozstawiają onsety ~0,12–0,26 s na słowo;
  headliny dziedziczą `typography_motion` sceny, body/kicker `fade-up`.
  QA pomija kolizje między fragmentami tego samego bloku (`split_from`).
- **Efekt „grawitacji"** = preset `pop-settle` (słowa opadają i stabilizują).
  Stosować **tylko do wybranych tekstów**, nie do wszystkiego.
- Sceny mają być zróżnicowane (różne kompozycje, ikony Lucide, dekoracje) —
  płaskie, same-tekstowe slajdy są uznawane za amatorskie.
- **Odrzucone dekoracje (2026-11-12)**: poziome kreski (`minus`), złote kropki,
  diamenty i pierścienie oraz dodane ikony na obrzeżach scen — właściciel
  uznał je za zbędne. Zostają tylko ikony merytoryczne (filary, checklista,
  landmark, message-circle-question) i logo. Nie dokładać „pojedynczych"
  elementów dekoracyjnych bez wyraźnej prośby.

## 3. Slajd logotypów banków (wzorzec do naśladowania)

- 14 logotypów banków z `/finansowanie/` w siatce 7×2, **jasne tło**
  (`#FFFFFF → #EEF0F2`) — ciemne logotypy są niewidoczne na graficie.
- Logotypy pojawiają się **wolno**: co ~0,38 s (nie gęściej), każdy z `enter.pop`
  ~0,4 s + **cichy whoosh** (`whoosh-soft.wav`, ~−25 dB) na każdym logo —
  życzenie właściciela z 2026-11-12. **Bez kliknięć** i bez whoosh'y na
  ruchach samej kamery (zmiany kątów/przejścia scen) — to były „dziwne".
- Logo **Erste**: asset na stronie jest białym sylwetą — w wizji ma być
  niebieski **#3465E4** (kolor z referencji właściciela); `logo-erste.png`
  przekolorowany, zapis w `provenance.json`.
- Scena `statement` z headline „OFERTY Z KILKU BANKÓW" i podtytułem
  „Wybieramy tę, która pasuje do Ciebie." — nie „porównujemy" (za sztucznie).
- Nie przywracać usuniętego slajdu ze zdjęciami Kalisz (polaroid_burst) bez
  wyraźnej prośby.

## 4. Jakość techniczna

- **Gradienty**: przy widocznych pasach bandingu ustawiać
  `export.pixel_format: "yuv420p10le"` (10-bit H.264, wymaga nowszego enkodera;
  `studio_output.py` już akceptuje ten format).
- **Dostawa na Facebooka**: 10-bit High 10 **nie jest odtwarzany** przez FB —
  na upload robić transkodowaną kopię 8-bit `yuv420p` + `+faststart`
  (np. `story-13-…-8bit.mp4`); master 10-bit zostaje do oceny na telefonie.
- Checklisty: silnik centuje blok wierszy pionowo (naprawione w
  `build_checklist`); znak cytatu pozycjonuj przez `quote_mark {x,y,w,h}`.
- Zawsze: `studio-qa --strict` (0 błędów), render MP4, storyboard + inspekcja
  klatek, a na końcu ogląd na telefonie z dźwiękiem (`docs/REVIEW_RUBRIC.md`).

## 5. Prawa i status materiałów

- Zdjęcia z ofert: `rights_status: "owner_permission"` (decyzja z 2026-11-12,
  zapis w `provenance.json` i `licensing/README.txt`).
- **Muzyka zostaje** (decyzja właściciela): `artmylife-powerful-dramatic-trailer`.
  Formalnie licencja niezweryfikowana — istotne tylko przy płatnych kampaniach.
- Nowe assety dopisuj do `imports/photos/provenance.json` + `licensing/README.txt`.

## 6. Nowe możliwości silnika (współdzielone, nie brandowe)

- `split_lines: true|"words"|[role,...]` w scenie — `true` rozbija na linie,
  `"words"` na pojedyncze słowa (realizacja w `_finish` → `_split_text_lines`,
  `src/reels_maker/components/scene_support.py`); fragmenty jednego bloku
  mają `meta.split_from` i są wyłączone z QA kolizji wzajemnych.
- `perspective`: `mode: settle|drift|push` + `path` (lista kluczowych klatek).
- `editorial_media[].enter`: `{delay, duration, style: pop|fade}` — stagger
  pojawiania się elementów graficznych.
- `cues`: `{rola: onset}` — ręczne rozstawienie animacji wejścia.
- `quote_mark`: pozycja znaku cytatu; `icon_library`/`icon_names`/`icon_assets`:
  ikony Lucide/material.
- `export.pixel_format`: `yuv420p` (domyślnie) lub `yuv420p10le`.
- `icon_assets[].enter`: `{delay, duration, style}` — animowane pojawianie się
  ikon (style = aliasy presetów: pop/fade/rise/slide/mask/cascade/scale).
- `audio.sfx`: `{file: "shared://audio/…", time, gain_db, source}` — sampy
  w `shared_media/audio/`: `ui-pop.wav` (wejścia słów), `ui-tick.wav`
  (filary/kroki), `ui-chime.wav` (CTA), `ui-whoosh.wav` (pojawienia logo)
  + `polaroid-shutter-click.mp3`. Wszystkie `*-soft.wav` (syntezowane v2)
  usunięte 2026-11-12 — właściciel wymaga SFX pobieranych z internetu
  (Mixkit, patrz `shared_media/README.md`).
- Dekoracyjne akcenty marki: `media/decor/accent-{dot,diamond,ring,rule}.png`
  (złoto #D8A356, transparentne) — używane przez `editorial_media` z `enter`.
  Uwaga: `editorial_media` wymaga w/h ≥ 0.02; ikony `icon_assets` kolidują
  z elementami tekstowymi — sprawdzaj `studio-qa` (safe zone + spacing).

## 7. Update 2026-11-12 — story-14 iteracja II (ruch, ikony, SFX, mapa)

- **Ciągły ruch**: `perspective.mode: "drift"` z `duration` ≈ długość sceny —
  sinusoidalny dryf kąta przez całą scenę (zero prędkości na zwrotach);
  `settle` zostawić tylko na scenach bookend (otwarcie/CTA).
- **Ikony rysowane**: `icon_draw: {duration, stagger}` na scenie (lub
  `icon_assets[].draw`) — silnik (`icon_strokes.py`) spłaszcza stroke'owe SVG
  (Lucide) na polylinie i rysuje je jako `path` nodes z `prop.progress`
  (trim_polyline). Onset biorą z `cues` roli ikony. Packi wypełnione
  (Material) fallbackują na raster. Nowe testy: `tests/test_icon_strokes.py`.
- **SFX z internetu, nie synteza**: właściciel odrzucił generowane sampy.
  Używać pobranych z licencjonowanych bibliotek — `shared_media/audio/ui-*.wav`
  to niezmodyfikowane downloady z Mixkit (patrz `shared_media/README.md`).
  Zasada: whoosh tylko na pojawieniach logo, nie na ruchu kamery.
- **Mapa lokacji**: `media/maps/piotrow-kalisz-map.png` — patrz sekcja 8
  (aktualnie: prawdziwa mapa OSM, nie schemat); używana jako `photo`
  w kompozycji `spotlight`.
- **Copy**: headline „DZIAŁKA POD DOM / 970 M² — UDZIAŁ OK. 485 M²",
  lokalizacja „Kalisz tuż obok. / Spokojna zabudowa i tereny otwarte.".

## 8. Update 2026-11-12 — story-14 iteracja III (korekta po przeglądzie)

- **Mapa = prawdziwa mapa OSM, nie rysunek**: `media/maps/piotrow-kalisz-map.png`
  to mozaika kafelków OpenStreetMap (geokodowanie Nominatim, zoom 11) ze
  złotą pinezką PIOTRÓW, niebieską KALISZ i przerywaną trasą; atrybucja ODbL
  na obrazie. Przy kolejnych lokalizacjach robić tak samo (OSM lub Google
  Static z kluczem) — nie rysować własnych schematów.
- **Scena mapy bez tekstu na mapie**: headline i body usunięte — zakrywały
  mapę. Zostaje tylko mały kicker u góry. Etykiety niosą same pinezki.
- **Korekta copy po scenach**:
  - sceny otwarcia: bez „NOWA OFERTA" i podobnych sztucznych etykiet;
  - checklista: **bez myślników** — separator to `·` („PARTER · 69,65 M²");
  - bez wypełniających podtytułów typu „wykończenie pod Ciebie" — zostaje
    samo „Stan deweloperski";
  - CTA: **„UMÓW SIĘ NA PREZENTACJĘ"** (nie „Umów prezentację tego domu").
- **Sceny do odrzucenia można wycinać w całości** — usunięcie sceny
  działki było lepsze niż jej "poprawianie"; nie oszczędzać słabych scen.
- **Liczby w `stats` mają być duże**: `stat_size_role: "hero"` (nowa opcja
  silnika w `build_stats`, także per-item `size_role`) zamiast domyślnego
  `title` — właściciel zażądał powiększenia samych cyfr.
- **Po wycięciu sceny**: przeliczyć `audio.sfx` od nowa (timestampy = start
  sceny + onset z `cues`) i przyciąć `cues` do faktycznych elementów
  (sprawdzić `studio-inspect`, które role powstają po `split_lines`).
- `validate` (plikowy format) nie dotyczy manifestów studio — używać
  `studio-qa --strict` + `studio-render`.

## 9. Update 2026-11-12 — story-15 (Szałe, ul. Wiśniówa) + uwagi techniczne

- **`photo_carousel` wymaga `"type": "photo_carousel"`** — samo
  `composition: "photo_carousel"` cicho spada do `statement` (bug w
  `_scene_type`, `scenes.py`). W story-14 scena 5 też była dotknięta —
  manifest poprawiony, MP4 do przerenderowania. Zawsze sprawdzać
  `component` w `studio-inspect` po dodaniu nowej kompozycji.
- **Ikony Lucide**: cache w `~/.cache/reels-maker/icon-libraries/`;
  brakujące dociągać ręcznie z
  `raw.githubusercontent.com/lucide-icons/lucide/0.468.0/icons/<name>.svg`.
  Użyte: `house`, `history`, `tree-palm` (nie `palmtree` — nie istnieje
  w lucide 0.468), `hammer`, `plug-zap`.
- **Oferty z "mini-domkiem"**: dane Szałe — 846 m² + domek 60 m² za
  295 000 zł; zdjęcie `OPIS-J` (karta z opisem) pomijane na życzenie
  właściciela; reszta galerii OK. Mapy OSM: geokodować ulicę, nie tylko
  miejscowość (precyzyjniejszy pinezek).
- **Słowa mają się różnić wizualnie**: fragmenty `split_lines:
  "words"` dziedziczyły jeden preset, więc akapity wyglądały na jeden
  blok. Silnik (`_split_text_lines`) naprzemiennie daje co drugiemu słowu
  inny preset z puli `slide-left/mask-rise/pop-settle/word-cascade/
  fade-up` (parzyste indeksy zachowują styl sceny). Stosować zawsze.
- **Tekstura papieru**: `media/textures/paper-light.png` (self-generated,
  ciepły off-white z włóknami) jako `photo` w `statement` + `theme:
  "light"` + `headline_size_role: "hero"` — przydatne dla „redakcyjnych"
  scen tekstowych.
- **Unikać bezsensownych statystyk**: „MEDIA 2" odrzucone — lepsze
  „DO KALISZA · 6 km" (liczone z geometrii).

## 10. Update 2026-11-12 — story-16 (Ociąż, gm. Nowe Skalmierzyce) + korekty

- **`stats` przyjmuje 1–4 pozycje** (silnik poprawiony 2026-11-12 —
  wcześniej wymuszał dokładnie 4). Liczba statystyk ma wynikać
  z faktów oferty — **nigdy nie dokładać wypełniaczy** („4 KIERUNKI"
  odrzucone). Jeśli jest tylko 3 sensowne dane, pokaż 3; powtórka
  tej samej wartości w innych jednostkach (2,8 ha = 28 tys. m²)
  też jest wypełniaczem. Staty redundujące z mapą można pominąć.
- **Zakaz banek w copy**: „DZIAŁKA Z LOTU PTASIA" odrzucone jako
  „debile" — unikać ozdobnych, nienaturalnych fraz w nagłówkach
  karuzeli; kicker „ZOBACZ TEREN" wystarczy.
- **Sceny bez treści wycinać**: „SKALA POD INWESTYCJĘ" nic nie
  mówiło — usunięte w całości (ta sama zasada co słabe sceny
  w story-14).
- **Mapa kontekstowa**: dla gruntów inwestycyjnych pokazać
  **szeroki zasięg z sąsiednimi miastami** (zoom 11, środek
  ~(51.70, 17.95): Ociąż + Kalisz + Ostrów Wielkopolski widoczne
  na mapie OSM), **tylko jedna pinezka** na sprzedawanym terenie,
  **bez linii połączonej** i bez pinezek miast. Jasna mapa OSM
  wymaga mocniejszego górnego scrim (~0.88 alpha na górze obrazu),
  inaczej kicker nie przechodzi QA kontrastu (min. 3.0:1).
- **CTA kanoniczne**: „UMÓJ SIĘ / NA PREZENTACJĘ" + linia
  „PREZENTACJA TERENU NA ŻYWO" (zamiast „POROZMAWIAJMY O TERENIE").
- **Korekty językowe**: „od głównej drogi" naturalniej niż
  „od drogi głównej"; listy z `·` zamiast myślników; nie zaczynać
  linii od separatora.
