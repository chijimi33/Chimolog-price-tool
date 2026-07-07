import json
import unittest

from chimolog_price_tool import get_chimolog_prices, render_csv


class ChimologPriceToolTest(unittest.TestCase):
    def test_normalizes_public_products_json(self):
        source = {
            "meta": {
                "total": 2,
                "discount_count": 1,
                "updated_at": "2026/07/07 05:54",
                "show_points": True,
                "themes": [
                    {"theme": "best", "display_name": "特におすすめ★5"},
                    {"theme": "ai", "display_name": "ローカルAI"},
                ],
            },
            "products": [
                {
                    "asin": "B000TEST01",
                    "title": "Discounted Product",
                    "affiliate_url": "https://www.amazon.co.jp/dp/B000TEST01",
                    "review_url": "https://chimolog.co/review/",
                    "category": "PCパーツ",
                    "themes": ["best", "ai"],
                    "image_url": "https://example.test/image.jpg",
                    "price": 8000,
                    "discount": {"ref_high": 10000, "rate_percent": 19.955},
                    "points": {"total": 240, "rate_percent": 2.9444444},
                    "fetched_at": "2026/07/07 00:05",
                },
                {
                    "asin": "B000TEST02",
                    "title": "Regular Product",
                    "affiliate_url": "https://amzn.to/example",
                    "review_url": "",
                    "category": "SSD",
                    "themes": [],
                    "image_url": "",
                    "price": None,
                    "discount": None,
                    "points": None,
                    "fetched_at": "2026/07/07 00:06",
                },
            ],
        }

        result = get_chimolog_prices(json_text=json.dumps(source, ensure_ascii=False))

        self.assertEqual(result["site"]["updated_at"], "2026/07/07 05:54")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["discount_count"], 1)

        first = result["items"][0]
        self.assertEqual(first["asin"], "B000TEST01")
        self.assertEqual(first["theme_labels"], ["特におすすめ★5", "ローカルAI"])
        self.assertEqual(first["price_yen"], 8000)
        self.assertEqual(first["reference_high_yen"], 10000)
        self.assertEqual(first["discount_amount_yen"], 2000)
        self.assertEqual(first["discount_rate_percent"], 20.0)
        self.assertEqual(first["points_rate_percent"], 2.9)
        self.assertEqual(first["product_url"], "https://www.amazon.co.jp/dp/B000TEST01")

        second = result["items"][1]
        self.assertFalse(second["is_discounted"])
        self.assertIsNone(second["price_yen"])
        self.assertIsNone(second["review_url"])

    def test_render_csv_flattens_theme_lists(self):
        result = {
            "items": [
                {
                    "asin": "B000TEST01",
                    "title": "Sample",
                    "category": "PCパーツ",
                    "themes": ["best", "ai"],
                    "theme_labels": ["特におすすめ★5", "ローカルAI"],
                    "price_yen": 8000,
                    "reference_high_yen": 10000,
                    "discount_amount_yen": 2000,
                    "discount_rate_percent": 20.0,
                    "is_discounted": True,
                    "points_total": 240,
                    "points_rate_percent": 3.0,
                    "fetched_at": "2026/07/07 00:05",
                    "product_url": "https://www.amazon.co.jp/dp/B000TEST01",
                    "review_url": None,
                    "image_url": None,
                }
            ]
        }

        csv_text = render_csv(result)

        self.assertIn("theme_codes,theme_labels", csv_text)
        self.assertIn("best; ai,特におすすめ★5; ローカルAI", csv_text)


if __name__ == "__main__":
    unittest.main()
