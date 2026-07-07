# Chimolog Amazon price tool

`chimolog_price_tool.py` mirrors Chimolog's public Amazon recommendation price data from:

https://chimolog.co/wp-content/price/

The source site checks Amazon prices about every 12 hours. This tool fetches the public `data/products.json` file and normalizes the fields for ChatGPT price research tasks.

The output includes:

- `price_yen`: current Amazon price shown by Chimolog
- `reference_high_yen`: previous/reference high price when a discount is detected
- `discount_amount_yen`: `reference_high_yen - price_yen`
- `discount_rate_percent`
- `points_total` and `points_rate_percent`
- `theme_labels`: readable recommendation theme labels such as `特におすすめ★5`

## Usage

```bash
python3 chimolog_price_tool.py
```

Output as CSV:

```bash
python3 chimolog_price_tool.py --format csv --output chimolog_products.csv
```

Markdown table for quick reading:

```bash
python3 chimolog_price_tool.py --format markdown
```

If your local Python cannot find a CA bundle, specify one explicitly:

```bash
python3 chimolog_price_tool.py --cafile /etc/ssl/cert.pem
```

As a last resort for this public price page:

```bash
python3 chimolog_price_tool.py --insecure-tls
```

Use from another Python script:

```python
from chimolog_price_tool import get_chimolog_prices

data = get_chimolog_prices()
for item in data["items"]:
    print(item["asin"], item["title"], item["price_yen"])
```

No third-party packages are required.

## GitHub Actions publishing

The workflow in `.github/workflows/publish-chimolog-products.yml` runs every 6 hours and commits static files under `public/`:

- `chimolog_products.json`
- `chimolog_products.csv`
- `index.html`

The JSON URL for ChatGPT Tasks will be:

```text
https://raw.githubusercontent.com/chijimi33/Chimolog-price-tool/main/public/chimolog_products.json
```

After pushing this repository to GitHub, run `Update Chimolog product data` once manually from the GitHub Actions tab.

If the workflow cannot push generated files, open:

```text
Settings -> Actions -> General -> Workflow permissions
```

Then set it to `Read and write permissions`.
