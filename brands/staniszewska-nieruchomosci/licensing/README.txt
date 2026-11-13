Document every external asset before placing it in a project-ready media folder:

- asset title and local filename
- author or rights holder
- original source URL
- licence or written permission, including intended platforms and paid use
- date checked and reviewer
- any attribution that must accompany publication

Photos shown in a property listing, website screenshots, logos and client
portraits are not automatically approved for reuse in video. Keep unreviewed
downloads in imports/ quarantine. Do not add an asset to media/asset-library.json
until its exact source, rights and delivery readiness have been reviewed.

Asset records — checked 2026-10-26
==================================

Logo
----
- Asset: official white logo, 300 x 78 px.
- Local files: `media/assets/logo_white-300x78.webp` (source) and
  `media/assets/logo_white-300x78.png` (renderer-compatible conversion).
- Rights holder: Staniszewska Nieruchomości, as represented by the official
  website; not independently confirmed.
- Source URL: https://staniszewskanieruchomosci.pl/wp-content/uploads/2024/04/logo_white-300x78.webp?ver=1790416777
- Permission: user instructed us to add the official brand logo. No separate
  licence document was supplied.
- Usage: white variant for dark backgrounds only; do not recolor. Other
  platforms or paid campaigns should follow the brand owner's approval.
- Attribution: none specified.
- Reviewer: project assistant; source and dimensions checked, 2026-10-26.

Music
-----
- Asset: `artmylife-powerful-dramatic-trailer-514242.mp3`.
- Local file: `media/audio/artmylife-powerful-dramatic-trailer-514242.mp3`.
- Rights holder: unknown. The filename contains `artmylife`, but this has not
  been independently verified as the artist or rights holder.
- Source: user-provided file copied from the user's Downloads folder; no
  original source URL or licence document was supplied.
- Licence and allowed use: unverified, including online, social, advertising,
  and paid use. Do not publish until the source licence or permission is
  confirmed for the intended channels.
- Technical details: MP3, stereo, 44.1 kHz, 132.415 seconds, 256 kb/s.
- Attribution: unknown; confirm before publication.
- Reviewer: project assistant; file metadata checked, 2026-10-26.

Lucide icons (pillars composition)
----------------------------------
- Assets: `store`, `warehouse`, `truck`, `factory` glyphs, outline style,
  rendered from pinned Lucide 0.468.0 sources at video build time.
- No local copies in this brand directory; the renderer resolves them
  through the shared pinned icon cache (`icon_library: lucide`).
- Rights holder: Lucide contributors.
- Source URLs: https://github.com/lucide-icons/lucide (per-icon files under
  `icons/<name>.svg` at tag 0.468.0).
- Licence: ISC (https://github.com/lucide-icons/lucide/blob/0.468.0/LICENSE);
  some Feather-derived glyphs may retain MIT notices. Attribution is required
  on publication — keep this record and credit Lucide where the channel
  requires it.
- Usage: monochrome recolor to brand gold `#D8A356` in one Reels scene;
  single stroke family, no logo use, no modification of glyph shapes.
- Reviewer: project assistant; names fetched and SVG-validated 2026-11-10.

Offer listing photos (plot sales)
---------------------------------
- Assets: photos downloaded from the official offer pages
  (staniszewskanieruchomosci.pl/estate_property/...) for the plot/land
  listings: Metalowców, Poznańska 10/3 and 8/1, Żydów, Chełmce, Szałe
  (działka z domkiem) and Ociąż.
- Local files: `imports/photos/<offer-folder>/` originals plus derived
  `-card.png` / `-polaroid.png` review derivatives; per-file source URLs are
  recorded in `imports/photos/provenance.json`.
- Rights holder: Staniszewska Nieruchomości (listing agent Aneta
  Staniszewska); underlying photo authors not independently confirmed.
- Permission: project owner instructed on 2026-11-12 (chat) to download the
  listing photos and confirmed they may be used in the clips.
- Usage: internal review clips and social stories for this brand's own
  offers; do not redistribute the raw photos outside this purpose.
- Attribution: none specified.
- Reviewer: project assistant; source pages checked 2026-11-12.

Update 2026-11-12 — music decision and photo rights
--------------------------------------------------
- Music: the project owner decided to keep
  `artmylife-powerful-dramatic-trailer-514242.mp3` in the story clips.
  Its licence is still unverified; this is an owner decision, not a
  licence confirmation. Re-check before paid campaigns.
- Photos: all 107 entries in `imports/photos/provenance.json` sourced from
  `/estate_property/` offer pages are now marked `owner_permission`
  following the owner's instruction to download and use the listing
  photos.

Update 2026-11-12 — financing page assets
-----------------------------------------
- `imports/photos/finansowanie/kalisz.webp` and the 28 bank logo files in
  `imports/photos/finansowanie/banki/` come from
  https://staniszewskanieruchomosci.pl/finansowanie/ and are marked
  `owner_permission` in `imports/photos/provenance.json` (139 entries
  total). Bank logos were normalized to transparent PNGs for the
  logo-wall scene in story-13.

Update 2026-11-12 — story-14 map and SFX
----------------------------------------
- `media/maps/piotrow-kalisz-map.png`: real OpenStreetMap map (ODbL) centred
  on Piotrów, gm. Blizanów (51.8146, 18.0537) and Kalisz (51.7599, 18.0957),
  zoom 11, stitched from tile.openstreetmap.org; gold/blue markers and a
  dashed route added by the project assistant, plus a baked-in vertical
  scrim. Attribution "© OpenStreetMap contributors" is rendered on the image
  as required by ODbL. Author of markers/scrim: project assistant.
- `shared_media/audio/ui-*.wav`: unmodified Mixkit downloads (see
  `shared_media/README.md` for item IDs and licence terms).

- `media/maps/szale-kalisz-map.png`: real OpenStreetMap map (ODbL) centred
  between ul. Wiśniowa, Szałe (51.7210, 18.1497) and Kalisz (51.7473, 18.0795),
  zoom 12, stitched from tile.openstreetmap.org; gold/blue markers (SZAŁE,
  KALISZ), dashed route and baked-in scrims added by the project assistant.
  Attribution "© OpenStreetMap contributors" rendered on the image as
  required by ODbL.
