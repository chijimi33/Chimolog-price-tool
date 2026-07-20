import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from scripts.build_public_data import build_public_data


class BuildPublicDataTest(unittest.TestCase):
    def test_reuses_previous_public_json_when_live_fetch_fails(self):
        previous = {
            "source_url": "https://chimolog.co/wp-content/price/",
            "data_url": "https://chimolog.co/wp-content/price/data/products.json",
            "fetched_at": "2026-07-19T19:30:35+00:00",
            "site": {
                "title": "Amazonセールおすすめ商品一覧 | ちもろぐ",
                "updated_at": "2026/07/20 00:06",
                "show_points": True,
                "total": 1,
                "discount_count": 0,
                "themes": [],
            },
            "count": 1,
            "discount_count": 0,
            "items": [
                {
                    "asin": "B000TEST01",
                    "title": "Previous Product",
                    "category": "PCパーツ",
                    "themes": [],
                    "theme_labels": [],
                    "price_yen": 1000,
                    "reference_high_yen": None,
                    "discount_amount_yen": None,
                    "discount_rate_percent": None,
                    "is_discounted": False,
                    "points_total": 30,
                    "points_rate_percent": 3.0,
                    "fetched_at": "2026/07/20 00:06",
                    "product_url": "https://www.amazon.co.jp/dp/B000TEST01",
                    "affiliate_url": "https://www.amazon.co.jp/dp/B000TEST01",
                    "review_url": None,
                    "image_url": None,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            json_path = output_dir / "chimolog_products.json"
            json_path.write_text(
                json.dumps(previous, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with mock.patch(
                "scripts.build_public_data.get_chimolog_prices",
                side_effect=urllib.error.URLError("timed out"),
            ):
                result = build_public_data(output_dir)

            self.assertEqual(result["fetched_at"], previous["fetched_at"])
            self.assertEqual(result["items"][0]["title"], "Previous Product")
            self.assertTrue((output_dir / "chimolog_products.csv").exists())
            self.assertTrue((output_dir / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
