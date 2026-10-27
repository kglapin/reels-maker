# LottieFiles animations in Reels Maker

## What works today

Reels Maker does **not** play Lottie JSON (`.json`) or dotLottie (`.lottie`)
files natively. `reels_maker.library.check_library()` rejects both formats on
purpose; a Lottie file must not be marked as a supported library asset.

There is a safe, non-native route for a **single, manually selected** public
animation: obtain a permitted video export for that exact animation, record its
source and licence, review it, and use the resulting video as an ordinary Studio
video background. This is a raster/video workflow, not vector playback; an MP4
export is opaque and will not preserve transparent vector layers.

```json
{
  "type": "spotlight",
  "duration": 4.0,
  "headline": "A short authored headline",
  "photo": "media/stock/lottiefiles-export.mp4",
  "photo_time": 0.5
}
```

The path is relative to the selected brand directory. Keep source downloads in
`brands/<slug>/imports/` quarantine until they pass the project's privacy,
rights and human-review gates. Put an approved, usable derivative in the
brand's normal media area and maintain matching rights/provenance and editorial
review records. A successful render or a `free` label is not rights approval.

## Select and clear each asset manually

1. Open the individual animation page from the [Featured Free
   Animations](https://lottiefiles.com/featured-free-animations) page. Do not
   download a batch based on the listing.
2. Confirm that the exact animation is publicly available for download, is not
   marked Premium/Marketplace-only, and has a licence that allows this exact
   use. Save the individual page URL, creator name, asset ID/name, download
   date, exact licence name/version/URL and a checksum of the downloaded file.
3. Review the [Lottie Simple License](https://lottiefiles.com/page/license)
   and the [LottieFiles Terms](https://lottiefiles.com/page/terms-and-conditions)
   as they apply on the download date. Public downloadable files may be covered
   by the Lottie Simple License, which grants broad use, including commercial
   use, but has same-licence/derivative-work conditions and does not authorize
   building a competing animation catalog. LottieFiles also restricts
   commercial use of work created or edited through its Free/Individual plan;
   do not confuse that service-plan permission with the licence for a specific
   public downloadable file. When the distinction is unclear, do not use the
   asset until the owner has confirmed the rights.
4. Attribution is encouraged even where the applicable Lottie Simple License
   does not require it. Record the creator and attribution text in the project
   provenance; include visible credits when required by the exact licence.
5. Use only an export/download path that the individual asset page and its
   current terms authorize. Do not scrape, enumerate, hotlink, or reverse
   engineer LottieFiles' catalog or download endpoints. LottieFiles' developer
   documentation directs catalog discovery to its UI or its authenticated MCP
   service, not scraping.
6. Obtain a human rights/editorial review before changing the asset's rights
   state to cleared/reviewed. Check whether the licence's share-alike terms are
   compatible with the finished video and its distribution. This document is
   workflow guidance, not legal advice.

Useful official references:

- [Lottie Simple License](https://lottiefiles.com/page/license)
- [LottieFiles Terms and Conditions](https://lottiefiles.com/page/terms-and-conditions)
- [Commercial Use Guide](https://help.lottiefiles.com/commercial-use-guide)
- [Discovering and downloading animations](https://help.lottiefiles.com/discovering-downloading-and-uploading-animations)
- [LottieFiles developer documentation](https://docs.lottiefiles.com/llms.txt)

## Native Lottie playback is future work

Native support needs a reviewed renderer, bounded JSON/dotLottie decompression,
safe asset-path handling, frame-accurate transparent RGBA output, deterministic
caching, unsupported-feature reporting and visual regression tests. It must
also preserve the original source, per-item licence and derivative provenance.
Do not enable `.json`/`.lottie` entries in the asset library until this path is
implemented and audited. In particular, assess renderer licensing before
adding a dependency: the `python-lottie` package is AGPL-3.0-or-later, and the
popular `rlottie` project has been archived. No third-party animation files are
included in this repository by this integration note.

The GitHub repository is currently public. Do not commit client/confidential
downloads or new licensed animation files until the owner resolves the privacy
gate in `README.md` and `docs/ROADMAP_STATUS.json`.
