#!/usr/bin/env python3
"""Fetch and normalize Chimolog's public Amazon recommendation prices."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_PAGE_URL = "https://chimolog.co/wp-content/price/"
DEFAULT_DATA_URL = "https://chimolog.co/wp-content/price/data/products.json"
DEFAULT_TIMEOUT = 20.0
COMMON_CA_BUNDLES = [
    "/etc/ssl/cert.pem",
    "/opt/homebrew/etc/openssl@3/cert.pem",
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/openssl@3/cert.pem",
    "/usr/local/etc/openssl/cert.pem",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

CSV_FIELDS = [
    "asin",
    "title",
    "category",
    "theme_codes",
    "theme_labels",
    "price_yen",
    "reference_high_yen",
    "discount_amount_yen",
    "discount_rate_percent",
    "is_discounted",
    "points_total",
    "points_rate_percent",
    "fetched_at",
    "product_url",
    "review_url",
    "image_url",
]


def fetch_text(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    cafile: str | None = None,
    insecure_tls: bool = False,
) -> str:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, headers=request_headers)
    urlopen_kwargs: dict[str, Any] = {"timeout": timeout}
    if urllib.parse.urlparse(url).scheme == "https":
        urlopen_kwargs["context"] = make_ssl_context(cafile=cafile, insecure_tls=insecure_tls)

    with urllib.request.urlopen(request, **urlopen_kwargs) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def make_ssl_context(*, cafile: str | None = None, insecure_tls: bool = False) -> ssl.SSLContext:
    if insecure_tls:
        return ssl._create_unverified_context()

    ca_bundle = cafile or find_ca_bundle()
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return ssl.create_default_context()


def find_ca_bundle() -> str | None:
    candidates = [
        os.environ.get("SSL_CERT_FILE"),
        ssl.get_default_verify_paths().cafile,
        *COMMON_CA_BUNDLES,
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def get_chimolog_prices(
    data_url: str = DEFAULT_DATA_URL,
    *,
    page_url: str = DEFAULT_PAGE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    json_text: str | None = None,
    cafile: str | None = None,
    insecure_tls: bool = False,
) -> dict[str, Any]:
    """Return normalized products from Chimolog's public price JSON."""

    if json_text is None:
        json_text = fetch_text(
            data_url,
            timeout=timeout,
            cafile=cafile,
            insecure_tls=insecure_tls,
        )

    data = json.loads(json_text)
    meta = data.get("meta") if isinstance(data, dict) else {}
    if not isinstance(meta, dict):
        meta = {}

    raw_products = data.get("products") if isinstance(data, dict) else []
    if not isinstance(raw_products, list):
        raw_products = []

    theme_names = theme_label_map(meta)
    items = [
        normalize_product(product, theme_names)
        for product in raw_products
        if isinstance(product, dict)
    ]

    return {
        "source_url": page_url,
        "data_url": data_url,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "site": {
            "title": "Amazonセールおすすめ商品一覧 | ちもろぐ",
            "updated_at": blank_to_none(meta.get("updated_at")),
            "show_points": bool(meta.get("show_points", False)),
            "total": parse_int(meta.get("total")),
            "discount_count": parse_int(meta.get("discount_count")),
            "themes": meta.get("themes") if isinstance(meta.get("themes"), list) else [],
        },
        "count": len(items),
        "discount_count": sum(1 for item in items if item["is_discounted"]),
        "items": items,
    }


def theme_label_map(meta: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    themes = meta.get("themes")
    if not isinstance(themes, list):
        return labels

    for theme in themes:
        if not isinstance(theme, dict):
            continue
        code = blank_to_none(theme.get("theme"))
        display_name = blank_to_none(theme.get("display_name"))
        if code and display_name:
            labels[code] = display_name
    return labels


def normalize_product(product: dict[str, Any], theme_names: dict[str, str]) -> dict[str, Any]:
    themes = parse_string_list(product.get("themes"))
    price_yen = parse_int(product.get("price"))

    discount = product.get("discount")
    if not isinstance(discount, dict):
        discount = None

    reference_high_yen = parse_int(discount.get("ref_high")) if discount else None
    discount_amount_yen = (
        max(reference_high_yen - price_yen, 0)
        if reference_high_yen is not None and price_yen is not None
        else None
    )
    discount_rate_percent = (
        round_float(discount.get("rate_percent"), digits=1) if discount else None
    )

    points = product.get("points")
    if not isinstance(points, dict):
        points = None

    affiliate_url = blank_to_none(product.get("affiliate_url"))

    return {
        "asin": blank_to_none(product.get("asin")),
        "title": blank_to_none(product.get("title")),
        "category": blank_to_none(product.get("category")),
        "themes": themes,
        "theme_labels": [theme_names.get(theme, theme) for theme in themes],
        "price_yen": price_yen,
        "reference_high_yen": reference_high_yen,
        "discount_amount_yen": discount_amount_yen,
        "discount_rate_percent": discount_rate_percent,
        "is_discounted": discount is not None,
        "points_total": parse_int(points.get("total")) if points else None,
        "points_rate_percent": round_float(points.get("rate_percent"), digits=1) if points else None,
        "fetched_at": blank_to_none(product.get("fetched_at")),
        "product_url": affiliate_url,
        "affiliate_url": affiliate_url,
        "review_url": blank_to_none(product.get("review_url")),
        "image_url": blank_to_none(product.get("image_url")),
    }


def parse_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    strings = []
    for item in value:
        text = blank_to_none(item)
        if text:
            strings.append(text)
    return strings


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def round_float(value: Any, *, digits: int) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def blank_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def render_json(result: dict[str, Any], *, indent: int = 2) -> str:
    return json.dumps(result, ensure_ascii=False, indent=indent)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for item in result["items"]:
        row = dict(item)
        row["theme_codes"] = "; ".join(item.get("themes") or [])
        row["theme_labels"] = "; ".join(item.get("theme_labels") or [])
        writer.writerow(row)
    return output.getvalue()


def render_markdown(result: dict[str, Any]) -> str:
    rows = [CSV_FIELDS]
    for item in result["items"]:
        row = dict(item)
        row["theme_codes"] = "; ".join(item.get("themes") or [])
        row["theme_labels"] = "; ".join(item.get("theme_labels") or [])
        rows.append([format_markdown_cell(row.get(field)) for field in CSV_FIELDS])

    widths = [max(len(str(row[index])) for row in rows) for index in range(len(CSV_FIELDS))]
    header = "| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(rows[0])) + " |"
    divider = "| " + " | ".join("-" * widths[index] for index in range(len(CSV_FIELDS))) + " |"
    body = [
        "| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)) + " |"
        for row in rows[1:]
    ]
    return "\n".join([header, divider, *body])


def format_markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", r"\|").replace("\n", " ")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mirror Chimolog's public Amazon recommendation prices.",
    )
    parser.add_argument("url", nargs="?", default=DEFAULT_DATA_URL, help="Chimolog products JSON URL")
    parser.add_argument(
        "-f",
        "--format",
        choices=("json", "csv", "markdown"),
        default="json",
        help="Output format",
    )
    parser.add_argument("-o", "--output", help="Write output to this file instead of stdout")
    parser.add_argument("--json-file", help="Read products JSON from a local file instead of fetching it")
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL, help="Human-facing Chimolog price page URL")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    parser.add_argument("--cafile", help="CA bundle path for TLS verification")
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        help="Disable TLS certificate verification if this local Python cannot find a CA bundle",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    return parser


def render_result(result: dict[str, Any], output_format: str, *, indent: int) -> str:
    if output_format == "json":
        return render_json(result, indent=indent)
    if output_format == "csv":
        return render_csv(result)
    if output_format == "markdown":
        return render_markdown(result)
    raise ValueError(f"Unsupported output format: {output_format}")


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        json_text = None
        if args.json_file:
            with open(args.json_file, "r", encoding="utf-8") as file:
                json_text = file.read()

        result = get_chimolog_prices(
            args.url,
            page_url=args.page_url,
            timeout=args.timeout,
            json_text=json_text,
            cafile=args.cafile,
            insecure_tls=args.insecure_tls,
        )
        rendered = render_result(result, args.format, indent=args.indent)

        if args.output:
            with open(args.output, "w", encoding="utf-8", newline="") as file:
                file.write(rendered)
        else:
            print(rendered)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
