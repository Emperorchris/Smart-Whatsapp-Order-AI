"""
Seed script: populates the database with 30 products across 6 categories.
Each product has at least 4 media items (images) and 1-2 videos, and variants with inventory.

Usage:
    python seed_products.py
"""

import asyncio
import random
import string
from decimal import Decimal

from app.db.db_engine import AsyncSessionLocal
from app.db.model.category_model import Category
from app.db.model.product_model import Product
from app.db.model.product_variant_model import ProductVariant
from sqlalchemy import select


def generate_tracking_id(name: str) -> str:
    prefix = name[:4].upper().replace(" ", "X")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"{prefix}-{suffix}"


# ---------------------------------------------------------------------------
# Media helpers – uses picsum for images, sample-videos.com for videos
# Each product gets a unique seed so thumbnails look different.
# ---------------------------------------------------------------------------

# Cloudinary videos with compression (q_50,w_480) to stay under WhatsApp's 16MB limit
SAMPLE_VIDEOS: list[str] = [
    "https://res.cloudinary.com/dibeyo2v1/video/upload/q_50,w_480/samples/dance-2.mp4",
    "https://res.cloudinary.com/dibeyo2v1/video/upload/q_50,w_480/samples/product-demo.mp4",
    "https://res.cloudinary.com/dibeyo2v1/video/upload/q_50,w_480/samples/unboxing.mp4",
]


def make_media(product_slug: str, image_count: int = 4) -> list[dict]:
    """Generate media items with real product images and videos.

    Images from Unsplash (product-focused):
    - Fashion: unsplash.com/search/photos/clothing
    - Hair: unsplash.com/search/photos/wig
    - Electronics: unsplash.com/search/photos/phone
    - Beauty: unsplash.com/search/photos/makeup
    - Home: unsplash.com/search/photos/kitchen
    - Bags: unsplash.com/search/photos/bag
    """
    media = []

    # Map slug to real Unsplash image URLs (high-quality, free images)
    unsplash_urls = {
        "ankaramidress": [
            "https://images.unsplash.com/photo-1566882213335-c919b43ee900?w=600&h=600&fit=crop",  # African fabric
            "https://images.unsplash.com/photo-1598717981562-0dcc53aadb1d?w=600&h=600&fit=crop",  # Colorful dress
            "https://images.unsplash.com/photo-1555274723-cff8c3da7360?w=600&h=600&fit=crop",  # Pattern detail
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=600&fit=crop",  # Layered fabrics
        ],
        "agbada3piece": [
            "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=600&h=600&fit=crop",  # Traditional attire
            "https://images.unsplash.com/photo-1608408740869-18ed159dd81e?w=600&h=600&fit=crop",  # Gold embroidery
            "https://images.unsplash.com/photo-1612336307429-8a88e8d08324?w=600&h=600&fit=crop",  # Men's formal
            "https://images.unsplash.com/photo-1607522369075-2615f42de01d?w=600&h=600&fit=crop",  # Premium fabric
        ],
        "menscasualpolo": [
            "https://images.unsplash.com/photo-1618865646553-fce051b2dd84?w=600&h=600&fit=crop",  # Polo shirt
            "https://images.unsplash.com/photo-1559256021-cd4628902d4a?w=600&h=600&fit=crop",  # Black shirt
            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=600&fit=crop",  # Navy color
            "https://images.unsplash.com/photo-1611871437281-38bda36207c6?w=600&h=600&fit=crop",  # Cotton texture
        ],
        "highwaistpalazzo": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",  # Wide leg trousers
            "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&h=600&fit=crop",  # Flowy fabric
            "https://images.unsplash.com/photo-1606402412314-8c84eb2e68d4?w=600&h=600&fit=crop",  # Black pants
            "https://images.unsplash.com/photo-1541193227802-69cd90dbb784?w=600&h=600&fit=crop",  # Burgundy tone
        ],
        "adiretiedye": [
            "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&h=600&fit=crop",  # Indigo dye
            "https://images.unsplash.com/photo-1590411398263-e26b8f4e5558?w=600&h=600&fit=crop",  # Tie-dye pattern
            "https://images.unsplash.com/photo-1551621585-b58c85f4e7e9?w=600&h=600&fit=crop",  # Kimono style
            "https://images.unsplash.com/photo-1517849845537-1d51a20414de?w=600&h=600&fit=crop",  # Traditional pattern
        ],
        "brazilianwavewig": [
            "https://images.unsplash.com/photo-1599599810694-b5ac4dd64b11?w=600&h=600&fit=crop",  # Long wavy hair
            "https://images.unsplash.com/photo-1503454537688-e6c6ff1e7178?w=600&h=600&fit=crop",  # Hair texture
            "https://images.unsplash.com/photo-1531299204812-e6e99eae9017?w=600&h=600&fit=crop",  # Wig styling
            "https://images.unsplash.com/photo-1599599810016-5d0374ffdab3?w=600&h=600&fit=crop",  # Close-up hair
        ],
        "bonestraight": [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=600&fit=crop",  # Straight hair
            "https://images.unsplash.com/photo-1529148482759-b2ae42b5a33d?w=600&h=600&fit=crop",  # Hair bundles
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=600&fit=crop",  # Hair close-up
            "https://images.unsplash.com/photo-1507288641669-fbf23a1dd958?w=600&h=600&fit=crop",  # Hair styling
        ],
        "pixiecut": [
            "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?w=600&h=600&fit=crop",  # Short wig
            "https://images.unsplash.com/photo-1605497787271-745a2d27ed12?w=600&h=600&fit=crop",  # Black hair
            "https://images.unsplash.com/photo-1599599810694-b5ac4dd64b11?w=600&h=600&fit=crop",  # Hair styling
            "https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?w=600&h=600&fit=crop",  # Modern cut
        ],
        "crochetpassiontwist": [
            "https://images.unsplash.com/photo-1516180712155-76015eb20651?w=600&h=600&fit=crop",  # Braids
            "https://images.unsplash.com/photo-1599599810694-b5ac4dd64b11?w=600&h=600&fit=crop",  # Twist braiding
            "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&h=600&fit=crop",  # Hair texture
            "https://images.unsplash.com/photo-1507288641669-fbf23a1dd958?w=600&h=600&fit=crop",  # Braid styling
        ],
        "hdlacefrontal": [
            "https://images.unsplash.com/photo-1599599810016-5d0374ffdab3?w=600&h=600&fit=crop",  # Lace detail
            "https://images.unsplash.com/photo-1520763185298-1b434c919afe?w=600&h=600&fit=crop",  # Hair closure
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=600&fit=crop",  # Wig styling
            "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=600&h=600&fit=crop",  # Hair installation
        ],
        "iphone15pro": [
            "https://images.unsplash.com/photo-1592286927505-1def25115558?w=600&h=600&fit=crop",  # Smartphone
            "https://images.unsplash.com/photo-1606933248051-5ce98e48a5d7?w=600&h=600&fit=crop",  # Phone camera
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=600&fit=crop",  # Tech gadget
            "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?w=600&h=600&fit=crop",  # Phone display
        ],
        "airpods": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop",  # Earbuds
            "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&h=600&fit=crop",  # Wireless earbuds
            "https://images.unsplash.com/photo-1487215078519-e21cc028cb29?w=600&h=600&fit=crop",  # Audio device
            "https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?w=600&h=600&fit=crop",  # Premium audio
        ],
        "powerbank": [
            "https://images.unsplash.com/photo-1591996095166-cdfba7db2000?w=600&h=600&fit=crop",  # Power bank
            "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&h=600&fit=crop",  # Tech gadget
            "https://images.unsplash.com/photo-1525966222134-fcaaef14cf81?w=600&h=600&fit=crop",  # Charger
            "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?w=600&h=600&fit=crop",  # USB device
        ],
        "phoneholder": [
            "https://images.unsplash.com/photo-1588156921496-87f82f32a87c?w=600&h=600&fit=crop",  # Phone stand
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=600&fit=crop",  # Mobile accessory
            "https://images.unsplash.com/photo-1606933248051-5ce98e48a5d7?w=600&h=600&fit=crop",  # Tech holder
            "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?w=600&h=600&fit=crop",  # Smartphone support
        ],
        "usbc": [
            "https://images.unsplash.com/photo-1625948515291-69613efd103f?w=600&h=600&fit=crop",  # USB cable
            "https://images.unsplash.com/photo-1556656793-08538906a9f8?w=600&h=600&fit=crop",  # Charging cable
            "https://images.unsplash.com/photo-1565043666747-69f6646db940?w=600&h=600&fit=crop",  # Cable detail
            "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?w=600&h=600&fit=crop",  # Tech accessory
        ],
        "facialcleansing": [
            "https://images.unsplash.com/photo-1556227702-6d2b3c3a7205?w=600&h=600&fit=crop",  # Skincare
            "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&h=600&fit=crop",  # Beauty products
            "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&h=600&fit=crop",  # Cosmetics
            "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=600&h=600&fit=crop",  # Beauty care
        ],
        "lipstick": [
            "https://images.unsplash.com/photo-1599599810694-b5ac4dd64b11?w=600&h=600&fit=crop",  # Makeup
            "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&h=600&fit=crop",  # Cosmetic products
            "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&h=600&fit=crop",  # Lipstick colors
            "https://images.unsplash.com/photo-1615634260444-22f4e5b267c6?w=600&h=600&fit=crop",  # Beauty makeup
        ],
        "facemask": [
            "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&h=600&fit=crop",  # Face mask
            "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&h=600&fit=crop",  # Skincare treatment
            "https://images.unsplash.com/photo-1596724244500-9a80e7e0e8b3?w=600&h=600&fit=crop",  # Beauty treatment
            "https://images.unsplash.com/photo-1535698208419-8a161ae34d39?w=600&h=600&fit=crop",  # Premium skincare
        ],
        "fragrance": [
            "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&h=600&fit=crop",  # Perfume bottle
            "https://images.unsplash.com/photo-1488840715967-65db15cf8c46?w=600&h=600&fit=crop",  # Fragrance
            "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&h=600&fit=crop",  # Luxury perfume
            "https://images.unsplash.com/photo-1557808172-ca3f003f4b13?w=600&h=600&fit=crop",  # Scent bottles
        ],
        "bodylotion": [
            "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&h=600&fit=crop",  # Body care
            "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&h=600&fit=crop",  # Lotion bottles
            "https://images.unsplash.com/photo-1596724244500-9a80e7e0e8b3?w=600&h=600&fit=crop",  # Skincare products
            "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&h=600&fit=crop",  # Cosmetic bottles
        ],
        "kitchenset": [
            "https://images.unsplash.com/photo-1596521576789-ca5e4f0a5e10?w=600&h=600&fit=crop",  # Cookware
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=600&fit=crop",  # Kitchen pots
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Kitchenware
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Cooking utensils
        ],
        "bedsheet": [
            "https://images.unsplash.com/photo-1585954293641-e8b3721496a0?w=600&h=600&fit=crop",  # Bed linens
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=600&fit=crop",  # Bedding
            "https://images.unsplash.com/photo-1515882636212-4ec6baf1b2a7?w=600&h=600&fit=crop",  # Luxe bedding
            "https://images.unsplash.com/photo-1618895917969-2dba4cc2dc0c?w=600&h=600&fit=crop",  # Cotton sheets
        ],
        "tablerunner": [
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Table decor
            "https://images.unsplash.com/photo-1565630436374-9b0064dc1e41?w=600&h=600&fit=crop",  # Home decor
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Dining table
            "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&h=600&fit=crop",  # Interior design
        ],
        "decorpillow": [
            "https://images.unsplash.com/photo-1585954293641-e8b3721496a0?w=600&h=600&fit=crop",  # Throw pillows
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Cushions
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=600&fit=crop",  # Home comfort
            "https://images.unsplash.com/photo-1618895917969-2dba4cc2dc0c?w=600&h=600&fit=crop",  # Soft furnishings
        ],
        "stainless": [
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=600&fit=crop",  # Stainless steel
            "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=600&h=600&fit=crop",  # Metal cookware
            "https://images.unsplash.com/photo-1596521576789-ca5e4f0a5e10?w=600&h=600&fit=crop",  # Kitchen appliances
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=600&fit=crop",  # Premium cookware
        ],
        "leatherhandbag": [
            "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&h=600&fit=crop",  # Leather handbag
            "https://images.unsplash.com/photo-1520649512674-5c5771c0a54d?w=600&h=600&fit=crop",  # Designer bag
            "https://images.unsplash.com/photo-1584917865735-30a500e5ee93?w=600&h=600&fit=crop",  # Luxury handbag
            "https://images.unsplash.com/photo-1611591437281-38bda36207c6?w=600&h=600&fit=crop",  # Brown leather
        ],
        "backpack": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",  # Backpack
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",  # Travel backpack
            "https://images.unsplash.com/photo-1520485686063-6f3ee727de95?w=600&h=600&fit=crop",  # School bag
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",  # Daypack
        ],
        "goldnecklace": [
            "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&h=600&fit=crop",  # Gold jewelry
            "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&h=600&fit=crop",  # Necklace
            "https://images.unsplash.com/photo-1515377905703-c511b6b891a1?w=600&h=600&fit=crop",  # Luxury jewelry
            "https://images.unsplash.com/photo-1578926078328-123d5f3f6f6b?w=600&h=600&fit=crop",  # Gold chain
        ],
        "designersunglasses": [
            "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&h=600&fit=crop",  # Sunglasses
            "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&h=600&fit=crop",  # Fashion eyewear
            "https://images.unsplash.com/photo-1508296695146-367ee90e585d?w=600&h=600&fit=crop",  # Designer shades
            "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&h=600&fit=crop",  # UV400 protection
        ],
    }

    # Get images for this product, fallback to generic if not found
    images = unsplash_urls.get(
        product_slug.lower(),
        [
            f"https://picsum.photos/seed/{product_slug}1/600/600",
            f"https://picsum.photos/seed/{product_slug}2/600/600",
            f"https://picsum.photos/seed/{product_slug}3/600/600",
            f"https://picsum.photos/seed/{product_slug}4/600/600",
        ],
    )

    # Add images
    for img_url in images[:image_count]:
        media.append({"url": img_url, "type": "image"})

    # Add videos (1-2 per product)
    if SAMPLE_VIDEOS:
        num_videos = random.randint(1, 2)
        chosen_videos = random.sample(
            SAMPLE_VIDEOS, min(num_videos, len(SAMPLE_VIDEOS))
        )
        for url in chosen_videos:
            media.append({"url": url, "type": "video"})

    return media


# ---------------------------------------------------------------------------
# Product data: 30 products across 6 Nigerian commerce categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"name": "Fashion", "description": "Clothing, shoes, and accessories"},
    {
        "name": "Hair & Wigs",
        "description": "Human hair, wigs, extensions, and hair accessories",
    },
    {
        "name": "Gadgets & Electronics",
        "description": "Phones, earbuds, chargers, and tech accessories",
    },
    {
        "name": "Beauty & Skincare",
        "description": "Skincare, makeup, fragrances, and body care",
    },
    {
        "name": "Home & Kitchen",
        "description": "Cookware, decor, bedding, and home essentials",
    },
    {
        "name": "Bags & Accessories",
        "description": "Handbags, jewelry, watches, and fashion accessories",
    },
]

# Each entry: (name, description, base_price, sku, category_name, tags, variants)
# Variants: list of (attributes_dict, price, inventory)
PRODUCTS = [
    # ── FASHION (5) ──────────────────────────────────────────────
    (
        "Ankara Midi Dress",
        "Vibrant Ankara print midi dress with a flattering A-line silhouette. Perfect for owambe and casual outings.",
        Decimal("15000.00"),
        "FASH-001",
        "Fashion",
        ["ankara", "dress", "midi", "fashion", "owambe", "aso ebi", "women", "african print", "gown"],
        [
            ({"size": "S", "color": "Orange Print"}, Decimal("15000.00"), 20),
            ({"size": "M", "color": "Orange Print"}, Decimal("15000.00"), 35),
            ({"size": "L", "color": "Orange Print"}, Decimal("15000.00"), 25),
            ({"size": "M", "color": "Blue Print"}, Decimal("15000.00"), 18),
            ({"size": "L", "color": "Blue Print"}, Decimal("15000.00"), 12),
        ],
    ),
    (
        "Agbada 3-Piece Set",
        "Premium agbada set with inner top, trouser, and flowing outer robe. Handwoven aso-oke fabric.",
        Decimal("45000.00"),
        "FASH-002",
        "Fashion",
        ["agbada", "aso oke", "men", "fashion", "native", "traditional", "yoruba", "owambe", "wedding"],
        [
            ({"size": "M", "color": "White/Gold"}, Decimal("45000.00"), 10),
            ({"size": "L", "color": "White/Gold"}, Decimal("45000.00"), 8),
            ({"size": "XL", "color": "White/Gold"}, Decimal("48000.00"), 5),
            ({"size": "L", "color": "Navy/Silver"}, Decimal("47000.00"), 7),
            ({"size": "XL", "color": "Navy/Silver"}, Decimal("49000.00"), 4),
        ],
    ),
    (
        "Men's Casual Polo Shirt",
        "Soft cotton polo shirt with embroidered logo. Breathable fabric perfect for Lagos weather.",
        Decimal("8500.00"),
        "FASH-003",
        "Fashion",
        ["polo", "shirt", "men", "casual", "cotton", "fashion", "top", "collar"],
        [
            ({"size": "M", "color": "Black"}, Decimal("8500.00"), 40),
            ({"size": "L", "color": "Black"}, Decimal("8500.00"), 30),
            ({"size": "M", "color": "White"}, Decimal("8500.00"), 35),
            ({"size": "L", "color": "Navy"}, Decimal("8500.00"), 25),
            ({"size": "XL", "color": "Navy"}, Decimal("9000.00"), 15),
        ],
    ),
    (
        "High-Waist Palazzo Trousers",
        "Flowy wide-leg palazzo trousers with elastic waist. Elegant and comfortable for any occasion.",
        Decimal("12000.00"),
        "FASH-004",
        "Fashion",
        ["palazzo", "trousers", "pants", "women", "wide leg", "fashion", "high waist", "office"],
        [
            ({"size": "S", "color": "Black"}, Decimal("12000.00"), 22),
            ({"size": "M", "color": "Black"}, Decimal("12000.00"), 30),
            ({"size": "L", "color": "Burgundy"}, Decimal("12000.00"), 18),
            ({"size": "M", "color": "Olive Green"}, Decimal("12500.00"), 15),
            ({"size": "L", "color": "Olive Green"}, Decimal("12500.00"), 10),
        ],
    ),
    (
        "Adire Tie-Dye Kimono",
        "Handcrafted adire kimono jacket with traditional Yoruba indigo tie-dye patterns. Unisex fit.",
        Decimal("18000.00"),
        "FASH-005",
        "Fashion",
        ["adire", "kimono", "tie dye", "indigo", "yoruba", "unisex", "fashion", "traditional", "jacket"],
        [
            ({"size": "Free Size", "color": "Indigo"}, Decimal("18000.00"), 15),
            ({"size": "Free Size", "color": "Brown"}, Decimal("18000.00"), 12),
            ({"size": "Free Size", "color": "Teal"}, Decimal("19000.00"), 8),
        ],
    ),
    # ── HAIR & WIGS (5) ─────────────────────────────────────────
    (
        "Brazilian Body Wave Wig",
        "Premium 100% virgin Brazilian body wave lace front wig. Pre-plucked hairline with baby hair.",
        Decimal("65000.00"),
        "HAIR-001",
        "Hair & Wigs",
        ["wig", "brazilian", "body wave", "lace front", "human hair", "hair", "women", "closure"],
        [
            (
                {"length": "16 inches", "color": "Natural Black"},
                Decimal("65000.00"),
                12,
            ),
            (
                {"length": "20 inches", "color": "Natural Black"},
                Decimal("78000.00"),
                10,
            ),
            ({"length": "24 inches", "color": "Natural Black"}, Decimal("92000.00"), 6),
            (
                {"length": "20 inches", "color": "#27 Honey Blonde"},
                Decimal("82000.00"),
                8,
            ),
            (
                {"length": "24 inches", "color": "#27 Honey Blonde"},
                Decimal("95000.00"),
                5,
            ),
        ],
    ),
    (
        "Bone Straight Bundles",
        "Grade 12A bone straight human hair bundles. Silky smooth, no shedding, no tangling.",
        Decimal("35000.00"),
        "HAIR-002",
        "Hair & Wigs",
        ["bone straight", "bundles", "human hair", "hair", "weave", "extension", "women", "straight"],
        [
            ({"length": "14 inches", "bundles": "3 Bundles"}, Decimal("35000.00"), 20),
            ({"length": "18 inches", "bundles": "3 Bundles"}, Decimal("45000.00"), 15),
            ({"length": "22 inches", "bundles": "3 Bundles"}, Decimal("55000.00"), 10),
            (
                {"length": "18 inches", "bundles": "4 Bundles + Closure"},
                Decimal("62000.00"),
                8,
            ),
            (
                {"length": "22 inches", "bundles": "4 Bundles + Closure"},
                Decimal("75000.00"),
                5,
            ),
        ],
    ),
    (
        "Pixie Cut Short Wig",
        "Trendy pixie cut wig with adjustable straps. Lightweight, breathable cap construction.",
        Decimal("22000.00"),
        "HAIR-003",
        "Hair & Wigs",
        ["pixie", "short wig", "wig", "women", "hair", "low cut", "bob", "fashion"],
        [
            ({"length": "6 inches", "color": "Jet Black"}, Decimal("22000.00"), 25),
            ({"length": "6 inches", "color": "Wine Red"}, Decimal("23000.00"), 15),
            ({"length": "8 inches", "color": "Jet Black"}, Decimal("25000.00"), 18),
            ({"length": "8 inches", "color": "Ombre Brown"}, Decimal("26000.00"), 10),
        ],
    ),
    (
        "Crochet Passion Twist Hair",
        "Pre-looped crochet passion twist braiding hair. Soft, natural-looking texture. 6 packs per set.",
        Decimal("8500.00"),
        "HAIR-004",
        "Hair & Wigs",
        ["crochet", "passion twist", "braids", "braiding hair", "hair", "women", "twist", "protective style"],
        [
            (
                {"length": "14 inches", "color": "1B Natural Black"},
                Decimal("8500.00"),
                40,
            ),
            (
                {"length": "18 inches", "color": "1B Natural Black"},
                Decimal("9500.00"),
                30,
            ),
            ({"length": "14 inches", "color": "T1B/30 Ombre"}, Decimal("9000.00"), 25),
            ({"length": "18 inches", "color": "T1B/27 Ombre"}, Decimal("10000.00"), 20),
        ],
    ),
    (
        "HD Lace Frontal 13x6",
        "Ultra-thin HD lace frontal closure. Invisible knots, melts into all skin tones.",
        Decimal("28000.00"),
        "HAIR-005",
        "Hair & Wigs",
        ["lace frontal", "HD lace", "closure", "hair", "frontal", "women", "13x6", "swiss lace"],
        [
            ({"length": "14 inches", "texture": "Straight"}, Decimal("28000.00"), 15),
            ({"length": "16 inches", "texture": "Straight"}, Decimal("32000.00"), 12),
            ({"length": "16 inches", "texture": "Body Wave"}, Decimal("33000.00"), 10),
            ({"length": "18 inches", "texture": "Body Wave"}, Decimal("36000.00"), 8),
        ],
    ),
    # ── GADGETS & ELECTRONICS (5) ────────────────────────────────
    (
        "Wireless Bluetooth Earbuds Pro",
        "Active noise cancellation, 36hr battery life with charging case. IPX5 waterproof.",
        Decimal("18500.00"),
        "GADG-001",
        "Gadgets & Electronics",
        ["earbuds", "bluetooth", "wireless", "headphone", "audio", "gadget", "ANC", "earphone", "music"],
        [
            ({"color": "Black"}, Decimal("18500.00"), 50),
            ({"color": "White"}, Decimal("18500.00"), 40),
            ({"color": "Navy Blue"}, Decimal("19000.00"), 25),
        ],
    ),
    (
        "20000mAh Power Bank",
        "Fast-charging power bank with USB-C and dual USB-A ports. LED display shows battery level.",
        Decimal("12000.00"),
        "GADG-002",
        "Gadgets & Electronics",
        ["power bank", "charger", "battery", "portable", "gadget", "USB", "fast charge", "phone"],
        [
            ({"color": "Black"}, Decimal("12000.00"), 60),
            ({"color": "White"}, Decimal("12000.00"), 45),
            ({"color": "Blue"}, Decimal("12500.00"), 30),
        ],
    ),
    (
        "Smart Watch Fitness Tracker",
        "Heart rate monitor, sleep tracking, SpO2 sensor. Water-resistant with 7-day battery life.",
        Decimal("25000.00"),
        "GADG-003",
        "Gadgets & Electronics",
        ["smart watch", "fitness", "tracker", "watch", "gadget", "health", "sports", "wearable"],
        [
            ({"color": "Black", "strap": "Silicone"}, Decimal("25000.00"), 30),
            ({"color": "Rose Gold", "strap": "Silicone"}, Decimal("25000.00"), 20),
            ({"color": "Silver", "strap": "Metal"}, Decimal("28000.00"), 15),
            ({"color": "Black", "strap": "Leather"}, Decimal("27000.00"), 12),
        ],
    ),
    (
        "Ring Light 18-Inch with Tripod",
        "Professional 18-inch LED ring light with adjustable tripod stand and phone holder. 3 color modes.",
        Decimal("15000.00"),
        "GADG-004",
        "Gadgets & Electronics",
        ["ring light", "tripod", "LED", "photography", "gadget", "content creator", "selfie", "video"],
        [
            ({"size": "18 inches", "type": "With Tripod"}, Decimal("15000.00"), 25),
            ({"size": "12 inches", "type": "With Tripod"}, Decimal("9500.00"), 35),
            (
                {"size": "18 inches", "type": "With Tripod + Remote"},
                Decimal("17000.00"),
                15,
            ),
        ],
    ),
    (
        "Portable Bluetooth Speaker",
        "360-degree surround sound, waterproof IPX7. 12-hour playtime with deep bass.",
        Decimal("14000.00"),
        "GADG-005",
        "Gadgets & Electronics",
        ["speaker", "bluetooth", "portable", "music", "gadget", "audio", "waterproof", "bass"],
        [
            ({"color": "Black"}, Decimal("14000.00"), 35),
            ({"color": "Red"}, Decimal("14000.00"), 20),
            ({"color": "Camouflage Green"}, Decimal("14500.00"), 15),
        ],
    ),
    # ── BEAUTY & SKINCARE (5) ────────────────────────────────────
    (
        "Glow Vitamin C Serum Set",
        "3-piece vitamin C skincare set: cleanser, serum, and moisturizer. For brighter, even-toned skin.",
        Decimal("16000.00"),
        "BEAU-001",
        "Beauty & Skincare",
        ["skincare", "vitamin C", "serum", "beauty", "glow", "brightening", "face", "moisturizer"],
        [
            ({"skin_type": "Normal/Combination"}, Decimal("16000.00"), 30),
            ({"skin_type": "Oily/Acne-Prone"}, Decimal("16500.00"), 25),
            ({"skin_type": "Dry/Sensitive"}, Decimal("17000.00"), 20),
        ],
    ),
    (
        "Matte Liquid Lipstick Collection",
        "Long-lasting matte liquid lipstick. Transfer-proof, lightweight formula. Set of 6 shades.",
        Decimal("9500.00"),
        "BEAU-002",
        "Beauty & Skincare",
        ["lipstick", "matte", "makeup", "beauty", "lip", "cosmetics", "women", "liquid lipstick"],
        [
            ({"shade": "Nude Collection (6 pcs)"}, Decimal("9500.00"), 40),
            ({"shade": "Bold Red Collection (6 pcs)"}, Decimal("9500.00"), 30),
            ({"shade": "Berry & Plum Collection (6 pcs)"}, Decimal("9500.00"), 25),
            ({"shade": "Mixed Favorites (6 pcs)"}, Decimal("10000.00"), 20),
        ],
    ),
    (
        "Shea Butter Body Cream (500ml)",
        "100% organic shea butter body cream infused with honey and coconut oil. Deep moisturizing.",
        Decimal("4500.00"),
        "BEAU-003",
        "Beauty & Skincare",
        ["shea butter", "body cream", "lotion", "beauty", "moisturizer", "skincare", "organic", "body"],
        [
            ({"scent": "Original Shea"}, Decimal("4500.00"), 60),
            ({"scent": "Lavender"}, Decimal("4800.00"), 40),
            ({"scent": "Coconut & Honey"}, Decimal("5000.00"), 35),
            ({"scent": "Unscented"}, Decimal("4500.00"), 30),
        ],
    ),
    (
        "Complete Makeup Brush Set",
        "Professional 15-piece makeup brush set with vegan bristles and PU leather case.",
        Decimal("12000.00"),
        "BEAU-004",
        "Beauty & Skincare",
        ["makeup brush", "brush set", "beauty", "cosmetics", "makeup", "tools", "foundation brush"],
        [
            ({"color": "Rose Gold"}, Decimal("12000.00"), 20),
            ({"color": "Black/Gold"}, Decimal("12000.00"), 25),
            ({"color": "Marble White"}, Decimal("13000.00"), 15),
        ],
    ),
    (
        "Oud Arabian Perfume Oil (50ml)",
        "Luxurious concentrated oud perfume oil. Long-lasting, alcohol-free. Unisex fragrance.",
        Decimal("8000.00"),
        "BEAU-005",
        "Beauty & Skincare",
        ["perfume", "oud", "fragrance", "beauty", "arabian", "oil", "scent", "unisex", "cologne"],
        [
            ({"variant": "Classic Oud"}, Decimal("8000.00"), 30),
            ({"variant": "Oud & Rose"}, Decimal("8500.00"), 25),
            ({"variant": "Oud & Musk"}, Decimal("8500.00"), 20),
            ({"variant": "Royal Oud (Premium)"}, Decimal("12000.00"), 10),
        ],
    ),
    # ── HOME & KITCHEN (5) ───────────────────────────────────────
    (
        "Non-Stick Cookware Set (10 pcs)",
        "Premium granite-coated non-stick cookware set. Includes pots, frying pans, and lids.",
        Decimal("32000.00"),
        "HOME-001",
        "Home & Kitchen",
        ["cookware", "pots", "non-stick", "kitchen", "home", "cooking", "frying pan", "granite"],
        [
            ({"color": "Black/Grey"}, Decimal("32000.00"), 15),
            ({"color": "Burgundy"}, Decimal("33000.00"), 12),
            ({"color": "Cream/Gold"}, Decimal("34000.00"), 8),
        ],
    ),
    (
        "Rechargeable Standing Fan 18-Inch",
        "Solar-compatible rechargeable standing fan. 8-hour battery, remote control, 3 speed settings.",
        Decimal("28000.00"),
        "HOME-002",
        "Home & Kitchen",
        ["fan", "rechargeable", "standing fan", "home", "solar", "electric", "cooling", "NEPA"],
        [
            ({"color": "White"}, Decimal("28000.00"), 20),
            ({"color": "Black"}, Decimal("28000.00"), 18),
            ({"color": "Blue"}, Decimal("29000.00"), 10),
        ],
    ),
    (
        "Luxury Bedsheet Set (6 pcs)",
        "Egyptian cotton feel bedsheet set: fitted sheet, flat sheet, 4 pillowcases. 300 thread count.",
        Decimal("18000.00"),
        "HOME-003",
        "Home & Kitchen",
        ["bedsheet", "bedding", "home", "bedroom", "cotton", "luxury", "pillowcase", "bed"],
        [
            ({"size": "King", "color": "White"}, Decimal("18000.00"), 20),
            ({"size": "Queen", "color": "White"}, Decimal("15000.00"), 25),
            ({"size": "King", "color": "Grey"}, Decimal("18000.00"), 15),
            ({"size": "King", "color": "Navy Blue"}, Decimal("18500.00"), 12),
            ({"size": "Queen", "color": "Blush Pink"}, Decimal("15500.00"), 18),
        ],
    ),
    (
        "Insulated Food Flask (800ml)",
        "Stainless steel vacuum insulated food flask. Keeps food hot for 12 hours. Leak-proof.",
        Decimal("7500.00"),
        "HOME-004",
        "Home & Kitchen",
        ["food flask", "flask", "thermos", "insulated", "kitchen", "home", "stainless steel", "lunch"],
        [
            ({"color": "Silver"}, Decimal("7500.00"), 40),
            ({"color": "Rose Gold"}, Decimal("8000.00"), 30),
            ({"color": "Matte Black"}, Decimal("8000.00"), 25),
        ],
    ),
    (
        "LED Rechargeable Desk Lamp",
        "Touch-control LED desk lamp with 3 brightness levels. USB charging port. Foldable design.",
        Decimal("6500.00"),
        "HOME-005",
        "Home & Kitchen",
        ["desk lamp", "LED", "lamp", "home", "office", "rechargeable", "light", "study"],
        [
            ({"color": "White"}, Decimal("6500.00"), 35),
            ({"color": "Black"}, Decimal("6500.00"), 30),
            ({"color": "Pink"}, Decimal("7000.00"), 20),
        ],
    ),
    # ── BAGS & ACCESSORIES (5) ───────────────────────────────────
    (
        "Leather Tote Handbag",
        "Genuine leather tote bag with inner zip compartment and detachable strap. Spacious and elegant.",
        Decimal("22000.00"),
        "BAGS-001",
        "Bags & Accessories",
        ["handbag", "tote", "leather", "bag", "women", "fashion", "purse", "accessories"],
        [
            ({"color": "Brown"}, Decimal("22000.00"), 15),
            ({"color": "Black"}, Decimal("22000.00"), 20),
            ({"color": "Burgundy"}, Decimal("23000.00"), 12),
            ({"color": "Cream"}, Decimal("23000.00"), 10),
        ],
    ),
    (
        "Stainless Steel Wrist Watch",
        "Classic unisex stainless steel wrist watch. Water-resistant 30m. Quartz movement.",
        Decimal("15000.00"),
        "BAGS-002",
        "Bags & Accessories",
        ["watch", "wrist watch", "stainless steel", "accessories", "unisex", "fashion", "timepiece"],
        [
            ({"color": "Silver/White Dial"}, Decimal("15000.00"), 20),
            ({"color": "Gold/Black Dial"}, Decimal("16000.00"), 15),
            ({"color": "Rose Gold/Pink Dial"}, Decimal("16000.00"), 12),
            ({"color": "Black/Green Dial"}, Decimal("15500.00"), 18),
        ],
    ),
    (
        "Laptop Backpack (USB Port)",
        "Water-resistant laptop backpack with built-in USB charging port. Fits up to 15.6-inch laptops.",
        Decimal("12500.00"),
        "BAGS-003",
        "Bags & Accessories",
        ["backpack", "laptop bag", "bag", "USB", "school", "office", "travel", "accessories"],
        [
            ({"color": "Black"}, Decimal("12500.00"), 30),
            ({"color": "Grey"}, Decimal("12500.00"), 25),
            ({"color": "Navy Blue"}, Decimal("13000.00"), 18),
        ],
    ),
    (
        "Gold-Plated Jewelry Set (4 pcs)",
        "Elegant gold-plated jewelry set: necklace, earrings, bracelet, and ring. Hypoallergenic.",
        Decimal("9500.00"),
        "BAGS-004",
        "Bags & Accessories",
        ["jewelry", "gold", "necklace", "earrings", "bracelet", "ring", "accessories", "women", "gift"],
        [
            ({"style": "Classic Chain"}, Decimal("9500.00"), 25),
            ({"style": "Cuban Link"}, Decimal("10500.00"), 20),
            ({"style": "Butterfly Pendant"}, Decimal("11000.00"), 15),
            ({"style": "Layered Minimalist"}, Decimal("10000.00"), 18),
        ],
    ),
    (
        "Designer Sunglasses (UV400)",
        "Premium UV400 polarized sunglasses with branded hard case. Multiple frame styles.",
        Decimal("7500.00"),
        "BAGS-005",
        "Bags & Accessories",
        ["sunglasses", "UV400", "shades", "accessories", "fashion", "eyewear", "polarized", "unisex"],
        [
            ({"frame": "Aviator", "color": "Gold/Brown"}, Decimal("7500.00"), 20),
            ({"frame": "Cat Eye", "color": "Black"}, Decimal("7500.00"), 25),
            ({"frame": "Round", "color": "Tortoise"}, Decimal("8000.00"), 15),
            (
                {"frame": "Oversized Square", "color": "Black/Gold"},
                Decimal("8500.00"),
                12,
            ),
        ],
    ),
]


async def seed():
    async with AsyncSessionLocal() as db:
        try:
            # ── 1. Create categories ────────────────────────────────
            cat_map = {}
            for cat_data in CATEGORIES:
                result = await db.execute(
                    select(Category).filter(Category.name == cat_data["name"])
                )
                existing = result.scalars().first()
                if existing:
                    cat_map[cat_data["name"]] = existing.id
                    print(f"  Category '{cat_data['name']}' already exists, skipping.")
                else:
                    cat = Category(
                        name=cat_data["name"], description=cat_data["description"]
                    )
                    db.add(cat)
                    await db.flush()
                    cat_map[cat_data["name"]] = cat.id
                    print(f"  Created category: {cat_data['name']}")

            # ── 2. Create products + variants ───────────────────────
            created = 0
            for name, desc, price, sku, cat_name, tags, variants in PRODUCTS:
                result = await db.execute(select(Product).filter(Product.sku == sku))
                existing = result.scalars().first()
                if existing:
                    name_slug = name.lower().replace(" ", "").replace("-", "")
                    existing.media = make_media(name_slug)
                    existing.tags = tags
                    print(f"  Updated media/tags for '{name}' (SKU: {sku})")
                    created += 1
                    continue

                name_slug = name.lower().replace(" ", "").replace("-", "")
                product = Product(
                    tracking_id=generate_tracking_id(name),
                    name=name,
                    description=desc,
                    price=price,
                    sku=sku,
                    category_id=cat_map.get(cat_name),
                    media=make_media(name_slug),
                    tags=tags,
                    is_active=True,
                )
                db.add(product)
                await db.flush()

                for attrs, v_price, inv_qty in variants:
                    variant = ProductVariant(
                        product_id=product.id,
                        attributes=attrs,
                        product_variant_price=v_price,
                        inventory_quantity=inv_qty,
                        low_stock_threshold=5,
                        is_active=True,
                    )
                    db.add(variant)

                created += 1
                print(f"  Created product: {name} ({len(variants)} variants)")

            await db.commit()
            print(
                f"\nDone! Seeded {created} new products across {len(CATEGORIES)} categories."
            )

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
