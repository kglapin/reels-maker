import os
import unittest
from unittest.mock import patch
from reels_maker.assets.stock_media import (
    search_pexels, search_pixabay, search_unsplash, composition_candidates,
    rank_assets, StockAsset)


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

    def test_pixabay_maps_metadata(self):
        with patch.dict(os.environ, {"PIXABAY_API_KEY":"test"}):
            def fetch(url, headers=None):
                self.assertIn("pixabay.com/api",url)
                return {"hits":[{"id":2,"previewURL":"https://p/s",
                    "pageURL":"https://p/page","user":"B","imageWidth":2400,
                    "imageHeight":1600,"largeImageURL":"https://p/l"}]}
            self.assertEqual(search_pixabay("industry",fetch=fetch)[0].provider,
                             "pixabay")

    def test_unsplash_maps_metadata(self):
        with patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY":"test"}):
            def fetch(url, headers=None):
                self.assertEqual(headers["Authorization"],"Client-ID test")
                return {"results":[{"id":"abc","urls":{"small":"https://u/s",
                  "full":"https://u/f"},"links":{"html":"https://u/page"},
                  "user":{"name":"C","links":{"html":"https://u/author"}},
                  "width":2400,"height":1600}]}
            self.assertEqual(search_unsplash("solar",fetch=fetch)[0].author,"C")

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


if __name__=="__main__":
    unittest.main()
