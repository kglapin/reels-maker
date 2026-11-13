# ASTA Energy — animacje: jak to działa

Hub techniczny marki w tym narzędziu. Tożsamość wizualną trzyma
[BRAND.md](/Users/kamilglapinski_mbp14/Documents/CODING/PROJECTS/reels-maker/brands/asta-energy/BRAND.md)
(kolor `#47A013`, Open Sans, umiar w ruchu), ten plik opisuje
**system animacji**: style, gdzie co leży, jak renderować i jak
przechodzi kontrolę jakości.

## Style klipów

- **Iso-explainer** — rzut izometryczny, jasne tło, elementy
  z [katalogu](/Users/kamilglapinski_mbp14/Documents/CODING/PROJECTS/reels-maker/brands/asta-energy/PROP-CATALOG.md)
  (230 obiektów: instalacje, budynki, narzędzia, ikony).
- **Foto-hook** — zdjęcia redakcyjne z bloga przeplatane ze scenami
  iso (mieszane manifesty, np. seria taktowanie).
- **Ekran końcowy** — minimalistyczny, zawsze z kontaktem
  **67 350 90 90** (zapisane w `src/reels_maker/iso/film.py`).

## Gdzie co leży

- `brands/asta-energy/projects/` — manifesty JSON (jedyne źródło
  prawdy o klipie: sceny, czasy, teksty — lektora nie ma).
- `renders/asta-energy/` — gotowe MP4 + storyboardy, per temat
  w osobnych folderach (`blog-taktowanie-iso/`, `prop-galeria/`…).
  Pliki robocze i sieroty lądują w `_support/`, nie w root.
- `brands/asta-energy/media/` — footage, stock, muzyka, FX.
- Silnik: `src/reels_maker/iso/` (światy, buildery, film),
  bramy: `tools/iso_prop_gate.py`, audyt: `tools/iso_layer_audit.py`.

## Render klipu

```bash
.venv/bin/python -m reels_maker studio-render \
  brands/asta-energy/projects/<manifest>.json \
  --output renders/asta-energy/<folder>/ \
  --profile final --jobs 4
```

Podgląd scen lub storyboard przed finałem:

```bash
.venv/bin/python -m reels_maker studio-render <manifest> \
  --output /tmp/podglad/ --profile preview --scenes 3,4
.venv/bin/python -m reels_maker storyboard <manifest> \
  --video <plik.mp4> --output <storyboard.png> [--motion-strip]
```

Format serii taktowanie: 1080×1920, 30 fps (ustawione w manifeście,
nie w brand.json).

## Nowy obiekt do galerii

```bash
.venv/bin/python tools/iso_gallery2.py props_<batch>.<prop> <NN-tytul>
.venv/bin/python tools/iso_prop_gate.py renders/asta-energy/prop-galeria/<plik>.png \
  --plate /tmp/plate-<tytul>.png --brief "<PINNED-BRIEF>" \
  --audit <batch>.<prop> [--ensemble nvidia-direct]
```

Brama puszcza dalej tylko przy 0: pixel pre-check, audyt warstw
(0 errorów) i jednomyślni sędziowie LLM. Zasady budowania
(zakaz elips-cieni, styki na zakładkę ≥0.005, kołnierze jako język
łączeń) spisuje [playbook](/Users/kamilglapinski_mbp14/Documents/CODING/PROJECTS/reels-maker/docs/iso-prop-playbook.md).

## Weryfikacja całości

```bash
.venv/bin/python tools/iso_corpus_verify.py   # pixel + audyt, 230/230
.venv/bin/python tools/iso_corpus_gate.py     # + ensemble sędziów
.venv/bin/python tools/iso_catalog.py         # regeneracja katalogu
```

Status z 2026-11-12: korpus 229 pass + 1 pass-override (panorama PV
zatwierdzona przez właściciela) = 230/230, 0 faili; suite 685
testów zielony poza 1 znanym środowiskowym (stray MP4).

## Kontakt

Infolinia na ekranie końcowym: **67 350 90 90**.

## Showcase: obiekty z katalogu w klipach

Dowolny z 230 elementów gra w klipie jedną linijką manifestu
(film `prop`, klucz z [katalogu](/Users/kamilglapinski_mbp14/Documents/CODING/PROJECTS/reels-maker/brands/asta-energy/PROP-CATALOG.md)):

```json
{"id": "s1", "type": "iso-explainer", "duration": 7.0, "t0": 0.0,
 "film": "prop", "prop": "props_heat_a.manifold", "snow": 0,
 "copy": {"title": "ROZDZIELACZ",
          "body": ["Mosiezna belka, 4 zawory"]}}
```

Silnik maluje ten sam builder co brama galerii (cokół + focus
z rejestru); nieznany klucz sypie `ValueError` zamiast cichego
złego renderu. Testy: `tests/test_iso_film_prop.py`.

Per scena (klucze manifestu, wszystkie opcjonalne poza `prop`):
`prop` (klucz lub lista `[{label, dx, dy}]` — pierwszy to hero,
reszta to dostawki), `camera` (`move`: push/pull/pan-left/pan-right/
still, `amount`, turntable `spin` w radianach (`0` = brak) —
wszystko ease 8 s), `zoom` dla foto (`amount`, `time`, `dir`:
in/out, kotwica `focus: [x, y]`, dryf `pan: [dx, dy]`; duotone 0.55,
narasta 1.2 s), `title_size` (domyślnie 52; 70 w ofercie),
`copy.body` jako stringi albo `{"text", "from": "left"|"right"}`,
`transition_out` (`type`: diagonal-wipe, whip-pan, split-slide,
radial-reveal, zoom-through, pixel-dissolve, color-takeover…,
`duration`, `anchor`, `direction`, `easing`).
