#!/usr/bin/env python3
"""Build static files for GitHub Pages."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chimolog_price_tool import get_chimolog_prices, render_csv


def build_public_data(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    result = get_chimolog_prices()

    (output_dir / "chimolog_products.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "chimolog_products.csv").write_text(
        render_csv(result),
        encoding="utf-8",
        newline="",
    )
    (output_dir / "index.html").write_text(render_index(result), encoding="utf-8")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    return result


def render_index(result: dict[str, Any]) -> str:
    site = result.get("site") or {}
    items = result.get("items") or []
    sample_rows = "\n".join(render_item_row(item) for item in items[:10])

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chimolog Amazon Price Data</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.6; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.25rem; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }}
    th {{ background: #f7f7f7; }}
  </style>
</head>
<body>
  <h1>Chimolog Amazon Price Data</h1>
  <p>ちもろぐの公開価格JSONを、ChatGPTの価格調査タスク向けに正規化したデータです。</p>
  <ul>
    <li>Source: <a href="{escape_attr(result.get("source_url"))}">{escape(result.get("source_url"))}</a></li>
    <li>Data source: <a href="{escape_attr(result.get("data_url"))}">{escape(result.get("data_url"))}</a></li>
    <li>Fetched at: <code>{escape(result.get("fetched_at"))}</code></li>
    <li>Site updated at: {escape(site.get("updated_at"))}</li>
    <li>Item count: {len(items)}</li>
    <li>Discount count: {escape(result.get("discount_count"))}</li>
  </ul>
  <p>
    <a href="./chimolog_products.json">chimolog_products.json</a>
    /
    <a href="./chimolog_products.csv">chimolog_products.csv</a>
  </p>
  <h2>Preview</h2>
  <table>
    <thead>
      <tr>
        <th>Product</th>
        <th>Category</th>
        <th>Themes</th>
        <th>Price</th>
        <th>Discount</th>
        <th>Points</th>
      </tr>
    </thead>
    <tbody>
      {sample_rows}
    </tbody>
  </table>
</body>
</html>
"""


def render_item_row(item: dict[str, Any]) -> str:
    product_name = item.get("title") or item.get("asin") or ""
    product_url = item.get("product_url") or ""
    product_cell = f'<a href="{escape_attr(product_url)}">{escape(product_name)}</a>' if product_url else escape(product_name)
    discount = ""
    if item.get("is_discounted"):
        discount = (
            f'{format_yen(item.get("reference_high_yen"))} -> '
            f'{format_yen(item.get("price_yen"))} '
            f'({format_percent(item.get("discount_rate_percent"))} off)'
        )

    return f"""<tr>
        <td>{product_cell}</td>
        <td>{escape(item.get("category"))}</td>
        <td>{escape(join_values(item.get("theme_labels")))}</td>
        <td>{format_yen(item.get("price_yen"))}</td>
        <td>{discount}</td>
        <td>{format_points(item)}</td>
      </tr>"""


def format_yen(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{int(value):,}円"
    except (TypeError, ValueError):
        return escape(value)


def format_percent(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return escape(value)


def format_points(item: dict[str, Any]) -> str:
    total = item.get("points_total")
    rate = item.get("points_rate_percent")
    if total is None and rate is None:
        return ""
    return f"{format_number(total)}pt ({format_percent(rate)})"


def format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return escape(value)


def join_values(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return ", ".join(str(value) for value in values)


def escape(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def escape_attr(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GitHub Pages files for Chimolog price data.")
    parser.add_argument("--output-dir", default="public", type=Path)
    args = parser.parse_args()

    result = build_public_data(args.output_dir)
    print(f"Wrote {result['count']} Chimolog items to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
