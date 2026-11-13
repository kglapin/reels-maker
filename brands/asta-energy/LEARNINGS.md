# ASTA Energy — learnings z iteracji wideo

## Rachunek / hook (asta-click-through-pv-v1)
- Właściciel odrzucił pierwszą wersję jako „beznadziejny" — wymaga
  zdecydowanie lepszej estetyki i przejść; zdjęcia realizacji tylko domowe.
- Rachunek ma być uproszczony (abstrakcyjne belki/placeholdery), bez
  dokładnych tekstów; jedyna „żywa" treść to kwota naliczana animacją
  (`counters` w scenie, nie tekst w PNG).
- Nagłówek sceny 1 przesunięty wyżej (`lift`).
- Przycisk pojawia się na środku, klik od razu uruchamia `transition_out`.
- Realizacje jako karty na środku (photo-carousel), bez tekstów, duża dynamika,
  minimum 10 pozycji.
- `imports/` to kwarantanna — zdjęcia domowe mają `rights_status: unknown`,
  wymagają zatwierdzenia właściciela przed publikacją.

## Iteracja v5 (kolejne uwagi właściciela)
- Tło ma być w kolorach marki: głęboka zieleń oparta na #47A013
  (#0C1D0A → #1B3D17), nie neutralna szarość.
- Nagłówek sceny 1: hero, 3 linie, `lift` ~0.26 (musi kończyć się nad
  górną krawędzią rachunku).
- Rachunek: wyższy (1450×1200), z tytułem „Rachunek za prąd", wciąż
  uproszczony; kwota = `counters` z `rotation` = kąt pochylenia karty.
- Zamiast burn: `exit.style: "tear"` (rozdarcie na dwie połowy);
  przycisk jest pod rachunkiem i pojawia się razem z rozdarciem.
- Przejście po kliknięciu: `color-takeover` z `anchor` w środku przycisku.
- Kursor: nowy asset (biała strzałka, ciemny kontur, miękkie cienie).
- Karuzela: `card_aspect: 1.0` + `photo_fit: "contain"` — zdjęcia w całości,
  bez ucinania logo.
- Muzyka: `audio.music.start` dobrany tak, by drop (~10,7 s utworu) wpadł
  na klik (4,85 s) → start ≈ 5,85.

## Korekta v5b — znak kąta licznika
- `node.rotation` w silniku ma **przeciwny znak** do `PIL.Image.rotate`:
  engine `+θ` pochyla górę w prawo (jak PIL `-θ`). Assety generowane
  PIL-em z `rotate(-2.4)` wymagają w manifeście `rotation: +2.4`, nie -2.4.
  Przy dopasowywaniu tekstu do nachylonego assetu zawsze weryfikować
  znaki empirycznie (deskew klatki), nie zakładać tej samej konwencji.

## Korekta v5c — rozdarcie i przycisk
- Przycisk musi być **bezpośrednio pod** rachunkiem (asset y=0.675, pill
  zaczyna się ~1% wysokości assetu); poprzednio nachodził na dolną krawędź
  i był w połowie schowany ZA rachunkiem.
- `tear` w rendererze: połówki rotują wokół środka szwu (peel ±3.2°),
  brzeg cięcia jest rysowany na połowkach PRZED rotacją (wiruje razem
  z papierem), szew ±7%, padding = swing rotacji + separacja.
- Anchor `color-takeover` i ripple/cursor target = środek przycisku
  (y≈0.727), nie środek assetu.

## Korekta v5d — przycisk ZA rachunkiem
- Przycisk ma być w warstwie POD rachunkiem i przestrzennie ZA jego
  powierzchnią (asset y=0.508, pill ~0.518-0.602 wewnątrz rachunku
  .35-.685) — niewidoczny, dopóki rozdarcie nie odsłoni szczeliny.
- Ripple/anchor/kursor target = środek pill (~y 0.56).
- Overlay order: button PRZED bill w `overlays[]` = pod spodem.

## Korekta v5e — button jak na stronie + tło z tokenów
- Przycisk wg tokenów asta-energy.pl: płaski #367E18 (action), hover
  #356A29, radius ~22% wysokości, weight 600, strzałka → po labelu
  (osobny asset button-hover.png pojawiający się przy dojeździe kursora).
- Tło scen: gradient #14271C → #14221A (kolory tokenów/site, nie
  zmyślone zielenie); design_overrides.background = #14221A.
- Źródło tokenów: wp-content/themes/asta-blocks (tokens.css, style.css).

## Korekta v5f — teksty i gradienty
- Wejścia tekstu: `mask-rise` (wycieranie z uciętymi glifami) i
  `pop-settle` (overshoot = przeskok) odrzucone przez właściciela.
  `typography_motion: "fade-up"` na scenach 1 i 3; nowe klucze sceny
  `entrance_presets` mapuje role→preset (cta/logo/body → fade-up).
- Gradienty: `export.pixel_format: "yuv420p10le"` usuwa pasma bandingu
  (10-bit H.264, profil high10).

## Korekta v5g
- Hover arrow na przycisku odrzucony przez właściciela — usunięty overlay
  button-hover.png; przycisk zostaje pojedynczy, płaski #367E18.

## v5h (2026-11-13)
- Rachunek: wyższy papier (1450×1500 asset, kartka 1150×1120), overlay rect aspect ~0.967; counter y .635 h .05 rotation +2.4.
- Rozdarcie: sep_max .30 — połówki rozchodzą się do końca, szew od górnej do dolnej krawędzi obiektu.
- Przejście: `radial-reveal` z anchor [0.5,0.56] (środek przycisku); scene1 duration 5.75 → transition_out .9 startuje dokładnie w kliknięciu 4.85.
- Karuzela: nowy klucz `carousel.card_scale` (0.6–1.6); v5h = 1.18, photo_fit contain bez zmian.
- CTA: nowy klucz `phone_size` (24–220 px); v5h = 144 (~×2), website "" usuwa stopkę.

## Lektor ElevenLabs (2026-11-13)
- Domyślny głos lektora ASTA Energy: ElevenLabs voice_id
  `xAVsdcJvD1uegu8lFEE2` (model `eleven_multilingual_v2`), zapisany w
  `brand.json → voiceover.elevenlabs` — `tts-generate --brand asta-energy`
  podchwytuje go automatycznie.
- Generowane pliki lądują w `imports/audio/` (quarantine) — wymagają
  odsłuchu i przeniesienia do `media/audio/` przed użyciem w projekcie.

## v5i (2026-11-13)
- Headline: `split_lines: "words"` — wyrazy wchodzą sekwencyjnie (fade-up per word).
- Tear fix: seam endpoints pinned do x=.5 na y=0 i y=height (jitter tylko w środku); peel 3.2→1.8° (duży peel domykał dół — dolne rogi połów się zsuwały); sep_max .30→.34. Zweryfikowane: szczelina jest nieprzerwana od górnej do dolnej krawędzi papieru.

## v5k (2026-11-13)
- BUGFIX krytyczny: `_split_text_lines` używał `copy.copy` — wszystkie fragmenty dzieliły `tracks` dict, więc per-word/line animacja NIGDY nie działała (wszystkie słowa dostawały track ostatniego elementu). Fix: `child.tracks = dict(original.tracks)` + `child.children = list(...)`. Regression test w test_split_text_words.
- Headline: `split_lines: "words"` + jawne `cues` headline-0..4 co ~0.2s — sekwencyjne pojawianie się wyrazów.
- CTA: `phone_size: 136` (144 px nie mieściło "67 350 90 90" w 1 linii — 849px > ~838px dostępnej szerokości; 136px = 807px). Zweryfikowane: telefon w 1 linii.

## v5l (2026-11-13)
- Word fragments: `entrance_distance` clamp do 10px (było 26px preset fade-up) — mniejszy rzut = brak pozornego "skoku" pozycji przy pojawianiu się wyrazów. Mechanizm istniał (`node.meta["entrance_distance"]`), użyty po raz pierwszy dla split-words.

## v5m (2026-11-13)
- Word cascade: nowy meta `entrance_duration_scale` (0.25–4.0) w apply_entrance; fragmenty wyrazów = 1.7 (fade ~0.64s zamiast ~0.38s). cues headline-0..4 co 0.32s — każdy wyraz to wyraźny beat, ostatni kończy ~2.2s przed rozdarciem 3.2s.
