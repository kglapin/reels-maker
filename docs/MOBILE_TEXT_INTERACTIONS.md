# Mobile-style text interactions in Studio

These are original, scene-graph animations inspired by general mobile editing
patterns. They do not use Apple artwork, interface screenshots, system sounds,
or proprietary fonts.

## Search / prompt field

Add a `search_field` object to a Studio scene. Use `type: "search_canvas"` for
a copy-free full-screen search-field shot; otherwise the component remains an
overlay on the chosen scene. Existing fields stay compatible;
`typing_profile` is optional (`steady`, `human`, `fast`). `human` adds
deterministic variation and short pauses at word boundaries/punctuation. The
measured caret follows the exact typed prefix, blinks after entry and the focus
outline settles down after the phrase is entered.

```json
{
  "type": "statement",
  "duration": 5,
  "headline": "A QUESTION TAKES SHAPE",
  "search_field": {
    "query": "Jak zmienia się zużycie energii?",
    "placeholder": "Szukaj",
    "typing_profile": "human",
    "typing_start": 0.65,
    "typing_duration": 1.8,
    "focus_outline": true,
    "blink_period": 0.38
  }
}
```

## Note writing and selection

Use the copy-free `note_canvas` scene type to avoid stacking note UI on top of a
second headline composition. The title and body type in sequence; the body uses
real measured glyph positions for the caret. An optional selection is revealed
as one or more measured highlight strips and endpoint handles; it can cross
automatic line wraps when the exact phrase is present in the rendered text.

```json
{
  "type": "note_canvas",
  "duration": 7,
  "theme": "light",
  "note_editor": {
    "title": "Ideas for the weekend",
    "text": "Collect a few thoughts while the idea is fresh. Keep the useful details, then select the sentence you want to revisit.",
    "typing_profile": "human",
    "caret": true,
    "selection": {"text": "select the sentence", "start": 4.6, "duration": 1.1}
  }
}
```

`note_editor` also accepts `width_ratio`, `height_ratio`, `center_x`, `center_y`,
`page_color`, `text_color`, `selection_color`, `title_size`, `body_size`,
`typing_start`, and `typing_duration`. If text does not fit at its authored size,
the build fails rather than silently shrinking it. Keep copy concise enough for
the intended phone-sized hold.

## Motion and sound restraint

Text is revealed as a single continuous type-in, not a loud sound per glyph.
When reviewed SFX are available, one low-level typing texture can cover a short
entry, with a single soft selection/confirmation accent only when the edit is
meaningful. Avoid firing effects for every caret blink or selected character.
Run Studio QA and inspect actual start/middle/settled frames before delivery.
