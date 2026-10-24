import os
import unittest
from unittest.mock import patch
from reels_maker.assets.stock_media import (
    search_pexels, search_pexels_videos, search_pixabay,
    search_pixabay_videos, search_unsplash, search_openverse,
    search_wikimedia_commons, track_unsplash_download,
    composition_candidates, rank_assets, StockAsset)


class StockMediaTests(unittest.TestCase):
    def test_pexels_maps_metadata_without_real_api_call(self):
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test"}):
            def fetch(url, headers=None):
                self.assertIn("api.pexels.com",url)
                self.assertEqual(headers["Authorization"],"test")
                return {"photos":[{"id":1,"src":{"medium":"https://p/x",
                  "original":"https://p/original"},"url":"https://p/photo",
                  "photographer":"A","width":1800,"height":2400}]}
            asset=search_pexels("solar",fetch=fetch)[0]
            self.assertEqual((asset.provider,asset.author,asset.width),
                             ("pexels","A",1800))

    def test_pexels_video_search_preserves_renditions_and_selects_best_mp4(self):
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test"}):
            def fetch(url, headers=None):
                self.assertIn("/v1/videos/search?", url)
                self.assertIn("orientation=portrait", url)
                self.assertEqual(headers["Authorization"], "test")
                return {"videos": [{"id": 7, "url": "video-page", "image": "thumb",
                    "width": 1080, "height": 1920, "duration": 8,
                    "user": {"name": "Camera Op", "url": "author"},
                    "video_files": [
                        {"link": "small", "width": 540, "height": 960, "fps": 24,
                         "file_type": "video/mp4", "quality": "sd"},
                        {"link": "large", "width": 1080, "height": 1920, "fps": 30,
                         "file_type": "video/mp4", "quality": "hd"}]}]}
            asset = search_pexels_videos("solar", orientation="portrait", fetch=fetch)[0]
            self.assertEqual((asset.media_type, asset.duration_seconds, asset.download_url),
                             ("video", 8, "large"))
            self.assertEqual([(item.width, item.height, item.fps) for item in asset.renditions],
                             [(540, 960, 24.0), (1080, 1920, 30.0)])

    def test_pixabay_maps_metadata(self):
        with patch.dict(os.environ, {"PIXABAY_API_KEY":"test"}):
            def fetch(url, headers=None):
                self.assertIn("pixabay.com/api",url)
                return {"hits":[{"id":2,"previewURL":"https://p/s",
                    "pageURL":"https://p/page","user":"B","imageWidth":2400,
                    "imageHeight":1600,"largeImageURL":"https://p/l"}]}
            self.assertEqual(search_pixabay("industry",fetch=fetch)[0].provider,
                             "pixabay")

    def test_pixabay_video_search_preserves_item_license_and_renditions(self):
        with patch.dict(os.environ, {"PIXABAY_API_KEY": "test"}):
            def fetch(url, headers=None):
                self.assertIn("/api/videos/?", url)
                self.assertIn("key=test", url)
                return {"hits": [{"id": 8, "pageURL": "video-page", "user": "Creator",
                    "duration": 12, "imageWidth": 1920, "imageHeight": 1080,
                    "videos": {"small": {"url": "small", "width": 640, "height": 360,
                        "size": 100, "thumbnail": "small-thumb"},
                        "large": {"url": "large", "width": 1920, "height": 1080,
                        "size": 900, "thumbnail": "large-thumb"}}}]}
            asset = search_pixabay_videos("solar", fetch=fetch)[0]
            self.assertEqual((asset.media_type, asset.duration_seconds, asset.download_url),
                             ("video", 12, "large"))
            self.assertEqual((asset.license, asset.license_url, asset.rights_status),
                             ("Pixabay Content License",
                              "https://pixabay.com/service/license-summary/", "unknown"))
            self.assertEqual(len(asset.renditions), 2)

    def test_unsplash_maps_metadata(self):
        with patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY":"test"}):
            def fetch(url, headers=None):
                self.assertEqual(headers["Authorization"],"Client-ID test")
                return {"results":[{"id":"abc","urls":{"small":"https://u/s",
                  "full":"https://u/f"},
                  "user":{"name":"C","links":{"html":"https://u/author"}},
                  "width":2400,"height":1600,
                  "links":{"html":"https://u/page",
                    "download_location":"https://api.unsplash.com/photos/abc/download"}}]}
            asset=search_unsplash("solar",fetch=fetch)[0]
            self.assertEqual(asset.author,"C")
            self.assertEqual(asset.preview_url,"https://u/s")
            self.assertEqual(asset.tracking_url,"https://api.unsplash.com/photos/abc/download")
            self.assertEqual(asset.rights_status,"unknown")
            self.assertIn("Unsplash attribution",asset.attribution)

    def test_unsplash_tracking_is_explicit_and_uses_official_location(self):
        asset=StockAsset("unsplash","abc","hotlinked","page","C",100,100,
                         "full","author",tracking_url="https://api.unsplash.com/download")
        with patch.dict(os.environ,{"UNSPLASH_ACCESS_KEY":"test"}):
            def fetch(url,headers):
                self.assertEqual(url,asset.tracking_url)
                self.assertEqual(headers["Authorization"],"Client-ID test")
                return {"ok":True}
            self.assertEqual(track_unsplash_download(asset,fetch=fetch),{"ok":True})

    def test_unsplash_tracking_routes_through_quota_client_without_cache_retry(self):
        asset=StockAsset("unsplash","abc","preview","page","C",100,100,
                         "full","author",tracking_url="https://api.unsplash.com/download")
        with patch.dict(os.environ,{"UNSPLASH_ACCESS_KEY":"test"}), \
                patch("reels_maker.assets.stock_media.provider_json", return_value={"ok":True}) as request:
            self.assertEqual(track_unsplash_download(asset), {"ok":True})
        request.assert_called_once_with(
            "unsplash", asset.tracking_url,
            {"Authorization":"Client-ID test","Accept-Version":"v1"},
            cache_response=False, retries=0)

    def test_commons_maps_per_file_license_metadata(self):
        def fetch(url,headers=None):
            self.assertIn("commons.wikimedia.org/w/api.php",url)
            self.assertIn("imageinfo",url)
            return {"query":{"pages":{"42":{"pageid":42,"imageinfo":[{
                "url":"https://upload.wikimedia.org/file.jpg",
                "thumburl":"https://upload.wikimedia.org/thumb.jpg",
                "descriptionurl":"https://commons.wikimedia.org/wiki/File:X",
                "width":1200,"height":800,"extmetadata":{
                    "Artist":{"value":"Artist"},"LicenseShortName":{"value":"CC BY-SA 4.0"},
                    "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
                    "Attribution":{"value":"<a href=\"source\">Artist / source</a>"}}}]}}}}
        asset=search_wikimedia_commons("solar",fetch=fetch)[0]
        self.assertEqual((asset.provider,asset.license,asset.author),
                         ("wikimedia_commons","CC BY-SA 4.0","Artist"))
        self.assertEqual(asset.license_url,"https://creativecommons.org/licenses/by-sa/4.0/")
        self.assertEqual(asset.attribution,"Artist / source")
        self.assertEqual(asset.provider_url,"https://commons.wikimedia.org")

    def test_commons_video_search_filters_by_filetype_and_mediatype(self):
        def fetch(url, headers=None):
            self.assertIn("filetype%3Avideo", url)
            self.assertIn("mediatype", url)
            return {"query": {"pages": {
                "7": {"pageid": 7, "imageinfo": [{
                    "url": "https://upload.wikimedia.org/clip.webm",
                    "thumburl": "https://upload.wikimedia.org/thumb.jpg",
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:C",
                    "width": 1920, "height": 1080, "mime": "video/webm",
                    "mediatype": "VIDEO",
                    "extmetadata": {"LicenseShortName": {"value": "CC BY 4.0"}}}]},
                "8": {"pageid": 8, "imageinfo": [{
                    "url": "https://upload.wikimedia.org/photo.jpg",
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:P",
                    "width": 100, "height": 100, "mime": "image/jpeg",
                    "mediatype": "BITMAP", "extmetadata": {}}]}}}}
        assets = search_wikimedia_commons("turbine", media_type="video", fetch=fetch)
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].media_type, "video")
        self.assertEqual(assets[0].download_url,
                         "https://upload.wikimedia.org/clip.webm")

    def test_commons_audio_search_returns_zero_dimension_audio_candidates(self):
        def fetch(url, headers=None):
            self.assertIn("filetype%3Aaudio", url)
            return {"query": {"pages": {
                "9": {"pageid": 9, "imageinfo": [{
                    "url": "https://upload.wikimedia.org/sfx.ogg",
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:S",
                    "width": 0, "height": 0, "mime": "application/ogg",
                    "mediatype": "AUDIO",
                    "extmetadata": {
                        "Artist": {"value": "Field Recordist"},
                        "LicenseShortName": {"value": "CC0"}}}]}}}}
        assets = search_wikimedia_commons("whoosh", media_type="audio", fetch=fetch)
        self.assertEqual(len(assets), 1)
        asset = assets[0]
        self.assertEqual((asset.media_type, asset.width, asset.height),
                         ("audio", 0, 0))
        self.assertEqual(asset.license, "CC0")
        self.assertEqual(asset.author, "Field Recordist")

    def test_commons_image_search_drops_video_and_audio_results(self):
        def fetch(url, headers=None):
            self.assertNotIn("filetype", url)
            return {"query": {"pages": {
                "1": {"pageid": 1, "imageinfo": [{
                    "url": "https://upload.wikimedia.org/photo.jpg",
                    "descriptionurl": "page", "width": 800, "height": 600,
                    "mediatype": "BITMAP", "extmetadata": {}}]},
                "2": {"pageid": 2, "imageinfo": [{
                    "url": "https://upload.wikimedia.org/clip.webm",
                    "descriptionurl": "page", "width": 800, "height": 600,
                    "mediatype": "VIDEO", "extmetadata": {}}]}}}}
        assets = search_wikimedia_commons("turbine", fetch=fetch)
        self.assertEqual([a.media_type for a in assets], ["image"])

    def test_commons_rejects_unknown_media_type(self):
        with self.assertRaises(ValueError):
            search_wikimedia_commons("x", media_type="document", fetch=lambda u, h: {})

    def test_openverse_preserves_item_level_rights_fields(self):
        def fetch(url,headers=None):
            self.assertIn("api.openverse.org/v1/images/",url)
            return {"results":[{"id":"ov-1","thumbnail":"thumb","url":"media",
                "foreign_landing_url":"source","creator":"Creator","width":640,
                "height":480,"license":"by","license_url":"license-url",
                "attribution":"<b>Creator</b>, CC BY"}]}
        asset=search_openverse("solar",fetch=fetch)[0]
        self.assertEqual((asset.provider,asset.license,asset.license_url),
                         ("openverse","by","license-url"))
        self.assertEqual(asset.attribution,"Creator, CC BY")
        self.assertEqual(asset.provider_url,"https://openverse.org")
        self.assertEqual(asset.rights_status, "unknown")
        self.assertEqual(asset.provenance()["rights_status"], "unknown")

    def test_search_metadata_never_clears_rights_without_bound_review(self):
        from reels_maker.assets.stock_media import apply_reviewed_rights_decision
        asset = StockAsset("openverse", "id", "thumb", "source", "Creator", 100, 100,
                           "media", "source", license="cc0")
        with self.assertRaises(ValueError):
            apply_reviewed_rights_decision(asset, {"decision": "cleared"})
        with self.assertRaises(ValueError):
            apply_reviewed_rights_decision(asset, {"provider": "openverse", "asset_id": "other",
                "source_url":"source", "download_url":"media",
                "decision": "cleared", "reviewer": "reviewer", "evidence": "ticket"})
        with self.assertRaisesRegex(ValueError, "allowed platforms"):
            apply_reviewed_rights_decision(asset, {"provider":"openverse", "asset_id":"id",
                "source_url":"source", "download_url":"media",
                "decision":"cleared", "reviewer":"reviewer", "review_date":"2026-10-23",
                "attribution":"Attribution not required under reviewed license.",
                "evidence":"review-42", "license":"CC0", "license_url":"https://example.org/license",
                "allowed_platforms":[]})
        reviewed = apply_reviewed_rights_decision(asset, {"provider": "openverse", "asset_id": "id",
            "source_url":"source", "download_url":"media",
            "decision": "cleared", "reviewer": "reviewer", "review_date":"2026-10-23",
            "evidence": "review-42", "attribution":"Creator, CC0 1.0",
            "license":"CC0 1.0",
            "license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
            "allowed_platforms":["instagram_reels"]})
        self.assertEqual(reviewed.rights_status, "cleared")
        self.assertEqual(reviewed.provenance()["rights_status"], "cleared")
        self.assertEqual(reviewed.provenance()["rights_decision"]["reviewer"], "reviewer")
        self.assertEqual(asset.rights_status, "unknown")

    def test_five_distinct_safe_layouts_and_focal_crop(self):
        variants=composition_candidates(2400,1600,1080,1920,
                                         focal_x=.85,focal_y=.35)
        self.assertEqual(len({v["layout"] for v in variants}),5)
        for v in variants:
            x,y,w,h=v["image_rect"]
            self.assertGreater(w,0);self.assertGreater(h,0)
            self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
            self.assertLessEqual(x+w,1080);self.assertLessEqual(y+h,1920)
            left,top,cw,ch=v["crop"]
            self.assertLessEqual(left+cw,2400)
            self.assertLessEqual(top+ch,1600)
            self.assertGreater(v["retained_fraction"],0)

    def test_ranking_prefers_portrait_for_portrait_slot(self):
        portrait=StockAsset("pexels","1","x","x","a",1200,2000,"x","x")
        landscape=StockAsset("pexels","2","x","x","b",2000,1200,"x","x")
        self.assertEqual(rank_assets([landscape,portrait],aspect=9/16)[0],
                         portrait)

    def test_credentials_required(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):
                search_pexels("cat")
            with self.assertRaises(RuntimeError):
                search_pexels_videos("cat")
            with self.assertRaises(RuntimeError):
                search_pixabay_videos("cat")


if __name__=="__main__":
    unittest.main()
