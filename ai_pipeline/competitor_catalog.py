"""Curated competitors for honest, category-aware mock scans.

Live scans discover competitors from search evidence. Mock mode has no web
evidence, so it uses these representative peer groups and labels its results as
simulated.
"""

from __future__ import annotations

import re


BRAND_PEERS: dict[str, list[str]] = {
    "notion": ["Asana", "ClickUp", "Trello", "Monday.com", "Jira", "Airtable"],
    "asana": ["Monday.com", "Trello", "ClickUp", "Jira", "Wrike", "Notion"],
    "monday": ["Asana", "ClickUp", "Trello", "Jira", "Wrike", "Notion"],
    "clickup": ["Asana", "Monday.com", "Trello", "Jira", "Wrike", "Notion"],
    "zara": ["H&M", "Uniqlo", "Mango", "COS", "Gap", "ASOS"],
    "hm": ["Zara", "Uniqlo", "Mango", "Gap", "ASOS", "Shein"],
    "uniqlo": ["Zara", "H&M", "Muji", "Gap", "COS", "Mango"],
    "mango": ["Zara", "H&M", "Uniqlo", "COS", "Massimo Dutti", "ASOS"],
    "asos": ["Zara", "H&M", "Shein", "Boohoo", "Mango", "Fashion Nova"],
    "shein": ["ASOS", "Zara", "H&M", "Boohoo", "Fashion Nova", "Temu"],
    "levis": ["Wrangler", "Lee", "Diesel", "Gap", "American Eagle", "Uniqlo"],
    "chanel": ["Dior", "Gucci", "Louis Vuitton", "Prada", "Saint Laurent", "Hermès"],
    "gucci": ["Louis Vuitton", "Chanel", "Dior", "Prada", "Saint Laurent", "Versace"],
    "noise": ["boAt", "Boult", "Fire-Boltt", "JBL", "OnePlus", "Realme"],
    "keka": ["greytHR", "Darwinbox", "Zoho People", "Rippling", "BambooHR", "Workday"],
    "nike": ["Adidas", "Puma", "Under Armour", "New Balance", "ASICS", "Lululemon"],
    "adidas": ["Nike", "Puma", "Under Armour", "New Balance", "ASICS", "Reebok"],
    "apple": ["Samsung", "Google Pixel", "OnePlus", "Xiaomi", "Huawei", "Motorola"],
    "samsung": ["Apple", "Google Pixel", "OnePlus", "Xiaomi", "Motorola", "Huawei"],
    "tesla": ["BYD", "Rivian", "Lucid", "BMW", "Mercedes-Benz", "Hyundai"],
    "spotify": ["Apple Music", "YouTube Music", "Amazon Music", "Deezer", "Tidal"],
    "netflix": ["Disney+", "Max", "Prime Video", "Apple TV+", "Hulu", "Paramount+"],
    "shopify": ["WooCommerce", "BigCommerce", "Wix", "Squarespace", "Adobe Commerce"],
}

CATEGORY_PEERS: list[tuple[tuple[str, ...], list[str]]] = [
    (("luxury", "designer", "couture", "haute couture"),
     ["Chanel", "Dior", "Gucci", "Louis Vuitton", "Prada", "Saint Laurent", "Hermès"]),
    (("sportswear", "athletic wear", "running shoes", "sneakers", "athleisure"),
     ["Nike", "Adidas", "Puma", "New Balance", "Under Armour", "ASICS", "Lululemon"]),
    (("fashion", "apparel", "clothing", "streetwear", "garment", "fashion brand"),
     ["Zara", "H&M", "Uniqlo", "Mango", "ASOS", "Levi's", "Gap"]),
    (("beauty", "cosmetic", "skincare", "makeup", "personal care"),
     ["Sephora", "Ulta Beauty", "Fenty Beauty", "Rare Beauty", "L'Oréal", "Glossier", "The Ordinary"]),
    (("project management", "task management", "team collaboration", "work management"),
     ["Asana", "Monday.com", "ClickUp", "Trello", "Jira", "Wrike", "Notion"]),
    (("laptop", "computer", "notebook pc"),
     ["Apple", "Dell", "Lenovo", "HP", "ASUS", "Acer", "Microsoft Surface"]),
    (("smartphone", "mobile phone", "phone", "mobile device"),
     ["Apple", "Samsung", "Google Pixel", "OnePlus", "Xiaomi", "Motorola"]),
    (("electric vehicle", "electric car", "automotive", "car brand"),
     ["Tesla", "BYD", "Rivian", "Hyundai", "BMW", "Mercedes-Benz", "Lucid"]),
    (("music streaming", "audio streaming"),
     ["Spotify", "Apple Music", "YouTube Music", "Amazon Music", "Deezer", "Tidal"]),
    (("video streaming", "streaming service", "streaming platform"),
     ["Netflix", "Disney+", "Max", "Prime Video", "Hulu", "Apple TV+"]),
    (("ecommerce platform", "online store platform", "e-commerce platform"),
     ["Shopify", "WooCommerce", "BigCommerce", "Wix", "Squarespace", "Adobe Commerce"]),
    (("crm", "customer relationship management"),
     ["Salesforce", "HubSpot", "Zoho CRM", "Microsoft Dynamics 365", "Pipedrive"]),
    (("hrms", "human resource management", "human resources", "payroll software", "hr software"),
     ["Keka", "greytHR", "Darwinbox", "Zoho People", "Rippling", "BambooHR", "Workday"]),
    (("consumer electronics", "wearable", "smartwatch", "earbuds", "audio products"),
     ["boAt", "Noise", "JBL", "Fire-Boltt", "OnePlus", "Realme", "Sony"]),
    (("digital marketing", "seo software", "marketing platform"),
     ["HubSpot", "Semrush", "Ahrefs", "Moz", "Mailchimp", "Klaviyo"]),
]


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def get_competitors(brand: str, category: str) -> list[str]:
    """Return a relevant peer list, excluding the brand being scanned."""
    brand_key = _key(brand)
    candidates = BRAND_PEERS.get(brand_key)
    if candidates is None:
        category_text = category.casefold()
        candidates = next(
            (peers for terms, peers in CATEGORY_PEERS if any(term in category_text for term in terms)),
            [],
        )
    return [
        name for name in candidates
        if _key(name) != brand_key
        and not (len(brand_key) > 3 and _key(name) in brand_key)
    ]
