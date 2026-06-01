"""
Seed script: populates the database with 30 products across 6 categories.
Each product has real images, tags for wide search, variants with inventory.

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
# Categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"name": "Fashion", "description": "Clothing, shoes, and accessories"},
    {"name": "Hair & Wigs", "description": "Human hair, wigs, extensions, and hair accessories"},
    {"name": "Gadgets & Electronics", "description": "Phones, earbuds, chargers, and tech accessories"},
    {"name": "Beauty & Skincare", "description": "Skincare, makeup, fragrances, and body care"},
    {"name": "Home & Kitchen", "description": "Cookware, decor, bedding, and home essentials"},
    {"name": "Bags & Accessories", "description": "Handbags, jewelry, watches, and fashion accessories"},
]


# ---------------------------------------------------------------------------
# Products: (name, description, price, sku, category, tags, media, variants)
# ---------------------------------------------------------------------------

PRODUCTS = [
    # ── FASHION (5) ──────────────────────────────────────────────
    {
        "name": "Ankara Midi Dress",
        "description": "Vibrant Ankara print midi dress with a flattering A-line silhouette. Perfect for owambe, aso-ebi, and casual outings.",
        "price": Decimal("15000.00"),
        "sku": "FASH-001",
        "category": "Fashion",
        "tags": ["ankara", "dress", "midi", "fashion", "owambe", "aso ebi", "women", "african print", "gown"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1590735213920-68192a487bc2?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1606902965551-dce093cda6e7?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "S", "color": "Orange Print"}, Decimal("15000.00"), 20),
            ({"size": "M", "color": "Orange Print"}, Decimal("15000.00"), 35),
            ({"size": "L", "color": "Orange Print"}, Decimal("15000.00"), 25),
            ({"size": "M", "color": "Blue Print"}, Decimal("15000.00"), 18),
            ({"size": "L", "color": "Blue Print"}, Decimal("15000.00"), 12),
        ],
    },
    {
        "name": "Agbada 3-Piece Set",
        "description": "Premium agbada set with inner top, trouser, and flowing outer robe. Handwoven aso-oke fabric with gold embroidery.",
        "price": Decimal("55000.00"),
        "sku": "FASH-002",
        "category": "Fashion",
        "tags": ["agbada", "aso oke", "men", "fashion", "native", "traditional", "yoruba", "owambe", "wedding"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1612336307429-8a88e8d08324?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1608408740869-18ed159dd81e?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "M", "color": "White/Gold"}, Decimal("55000.00"), 10),
            ({"size": "L", "color": "White/Gold"}, Decimal("55000.00"), 8),
            ({"size": "XL", "color": "White/Gold"}, Decimal("58000.00"), 5),
            ({"size": "L", "color": "Navy/Silver"}, Decimal("57000.00"), 7),
            ({"size": "XL", "color": "Navy/Silver"}, Decimal("60000.00"), 4),
        ],
    },
    {
        "name": "Men's Casual Polo Shirt",
        "description": "Soft cotton polo shirt with embroidered logo. Breathable fabric perfect for Lagos weather.",
        "price": Decimal("9500.00"),
        "sku": "FASH-003",
        "category": "Fashion",
        "tags": ["polo", "shirt", "men", "casual", "cotton", "fashion", "top", "collar"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1625910513413-5fc421e0c5fd?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1618517351616-38fb9c5210c6?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "M", "color": "Black"}, Decimal("9500.00"), 40),
            ({"size": "L", "color": "Black"}, Decimal("9500.00"), 30),
            ({"size": "M", "color": "White"}, Decimal("9500.00"), 35),
            ({"size": "L", "color": "Navy"}, Decimal("9500.00"), 25),
            ({"size": "XL", "color": "Navy"}, Decimal("10000.00"), 15),
        ],
    },
    {
        "name": "High-Waist Palazzo Trousers",
        "description": "Flowy wide-leg palazzo trousers with elastic waist. Elegant and comfortable for any occasion.",
        "price": Decimal("13000.00"),
        "sku": "FASH-004",
        "category": "Fashion",
        "tags": ["palazzo", "trousers", "pants", "women", "wide leg", "fashion", "high waist", "office"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1551854838-212c50b4c184?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "S", "color": "Black"}, Decimal("13000.00"), 22),
            ({"size": "M", "color": "Black"}, Decimal("13000.00"), 30),
            ({"size": "L", "color": "Burgundy"}, Decimal("13000.00"), 18),
            ({"size": "M", "color": "Olive Green"}, Decimal("13500.00"), 15),
            ({"size": "L", "color": "Olive Green"}, Decimal("13500.00"), 10),
        ],
    },
    {
        "name": "Adire Tie-Dye Kimono",
        "description": "Handcrafted adire kimono jacket with traditional Yoruba indigo tie-dye patterns. Unisex fit.",
        "price": Decimal("20000.00"),
        "sku": "FASH-005",
        "category": "Fashion",
        "tags": ["adire", "kimono", "tie dye", "indigo", "yoruba", "unisex", "fashion", "traditional", "jacket"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1590411398263-e26b8f4e5558?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1517849845537-1d51a20414de?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "Free Size", "color": "Indigo"}, Decimal("20000.00"), 15),
            ({"size": "Free Size", "color": "Brown"}, Decimal("20000.00"), 12),
            ({"size": "Free Size", "color": "Teal"}, Decimal("22000.00"), 8),
        ],
    },

    # ── HAIR & WIGS (5) ─────────────────────────────────────────
    {
        "name": "Brazilian Body Wave Wig",
        "description": "Premium 100% virgin Brazilian body wave lace front wig. Pre-plucked hairline with baby hair. 150% density.",
        "price": Decimal("75000.00"),
        "sku": "HAIR-001",
        "category": "Hair & Wigs",
        "tags": ["wig", "brazilian", "body wave", "lace front", "human hair", "hair", "women", "closure"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1595959183082-7b570b7e1e19?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"length": "16 inches", "color": "Natural Black"}, Decimal("75000.00"), 12),
            ({"length": "20 inches", "color": "Natural Black"}, Decimal("90000.00"), 10),
            ({"length": "24 inches", "color": "Natural Black"}, Decimal("110000.00"), 6),
            ({"length": "20 inches", "color": "#27 Honey Blonde"}, Decimal("95000.00"), 8),
            ({"length": "24 inches", "color": "#27 Honey Blonde"}, Decimal("115000.00"), 5),
        ],
    },
    {
        "name": "Bone Straight Bundles",
        "description": "Grade 12A bone straight human hair bundles. Silky smooth, no shedding, no tangling. Can be dyed and bleached.",
        "price": Decimal("40000.00"),
        "sku": "HAIR-002",
        "category": "Hair & Wigs",
        "tags": ["bone straight", "bundles", "human hair", "hair", "weave", "extension", "women", "straight"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1519735777090-ec97162dc266?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1605497787271-745a2d27ed12?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1562004760-aceed7bb0fe3?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"length": "14 inches", "bundles": "3 Bundles"}, Decimal("40000.00"), 20),
            ({"length": "18 inches", "bundles": "3 Bundles"}, Decimal("52000.00"), 15),
            ({"length": "22 inches", "bundles": "3 Bundles"}, Decimal("65000.00"), 10),
            ({"length": "18 inches", "bundles": "4 Bundles + Closure"}, Decimal("72000.00"), 8),
            ({"length": "22 inches", "bundles": "4 Bundles + Closure"}, Decimal("85000.00"), 5),
        ],
    },
    {
        "name": "Pixie Cut Short Wig",
        "description": "Trendy pixie cut wig with adjustable straps. Lightweight, breathable cap construction. Beginner-friendly.",
        "price": Decimal("25000.00"),
        "sku": "HAIR-003",
        "category": "Hair & Wigs",
        "tags": ["pixie", "short wig", "wig", "women", "hair", "low cut", "bob", "fashion"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"length": "6 inches", "color": "Jet Black"}, Decimal("25000.00"), 25),
            ({"length": "6 inches", "color": "Wine Red"}, Decimal("26000.00"), 15),
            ({"length": "8 inches", "color": "Jet Black"}, Decimal("28000.00"), 18),
            ({"length": "8 inches", "color": "Ombre Brown"}, Decimal("29000.00"), 10),
        ],
    },
    {
        "name": "Crochet Passion Twist Hair",
        "description": "Pre-looped crochet passion twist braiding hair. Soft, natural-looking texture. 6 packs per set.",
        "price": Decimal("9500.00"),
        "sku": "HAIR-004",
        "category": "Hair & Wigs",
        "tags": ["crochet", "passion twist", "braids", "braiding hair", "hair", "women", "twist", "protective style"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1516180712155-76015eb20651?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1611432532930-95b54adcc0f8?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"length": "14 inches", "color": "1B Natural Black"}, Decimal("9500.00"), 40),
            ({"length": "18 inches", "color": "1B Natural Black"}, Decimal("11000.00"), 30),
            ({"length": "14 inches", "color": "T1B/30 Ombre"}, Decimal("10000.00"), 25),
            ({"length": "18 inches", "color": "T1B/27 Ombre"}, Decimal("11500.00"), 20),
        ],
    },
    {
        "name": "HD Lace Frontal 13x6",
        "description": "Ultra-thin HD lace frontal closure. Invisible knots, melts into all skin tones. Swiss lace.",
        "price": Decimal("32000.00"),
        "sku": "HAIR-005",
        "category": "Hair & Wigs",
        "tags": ["lace frontal", "HD lace", "closure", "hair", "frontal", "women", "13x6", "swiss lace"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1595959183082-7b570b7e1e19?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"length": "14 inches", "texture": "Straight"}, Decimal("32000.00"), 15),
            ({"length": "16 inches", "texture": "Straight"}, Decimal("36000.00"), 12),
            ({"length": "16 inches", "texture": "Body Wave"}, Decimal("37000.00"), 10),
            ({"length": "18 inches", "texture": "Body Wave"}, Decimal("40000.00"), 8),
        ],
    },

    # ── GADGETS & ELECTRONICS (5) ────────────────────────────────
    {
        "name": "Wireless Bluetooth Earbuds Pro",
        "description": "Active noise cancellation, 36hr battery life with charging case. IPX5 waterproof. Touch controls.",
        "price": Decimal("22000.00"),
        "sku": "GADG-001",
        "category": "Gadgets & Electronics",
        "tags": ["earbuds", "bluetooth", "wireless", "headphone", "audio", "gadget", "ANC", "earphone", "music"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black"}, Decimal("22000.00"), 50),
            ({"color": "White"}, Decimal("22000.00"), 40),
            ({"color": "Navy Blue"}, Decimal("23000.00"), 25),
        ],
    },
    {
        "name": "20000mAh Power Bank",
        "description": "Fast-charging power bank with USB-C PD and dual USB-A ports. LED display shows battery level.",
        "price": Decimal("15000.00"),
        "sku": "GADG-002",
        "category": "Gadgets & Electronics",
        "tags": ["power bank", "charger", "battery", "portable", "gadget", "USB", "fast charge", "phone"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1625961332771-3f40b0e2bdcf?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black"}, Decimal("15000.00"), 60),
            ({"color": "White"}, Decimal("15000.00"), 45),
            ({"color": "Blue"}, Decimal("15500.00"), 30),
        ],
    },
    {
        "name": "Smart Watch Fitness Tracker",
        "description": "Heart rate monitor, sleep tracking, SpO2 sensor. Water-resistant IP68 with 7-day battery life.",
        "price": Decimal("28000.00"),
        "sku": "GADG-003",
        "category": "Gadgets & Electronics",
        "tags": ["smart watch", "fitness", "tracker", "watch", "gadget", "health", "sports", "wearable"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1546868871-af0de0ae72be?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1617043786394-f977fa12eddf?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black", "strap": "Silicone"}, Decimal("28000.00"), 30),
            ({"color": "Rose Gold", "strap": "Silicone"}, Decimal("28000.00"), 20),
            ({"color": "Silver", "strap": "Metal"}, Decimal("32000.00"), 15),
            ({"color": "Black", "strap": "Leather"}, Decimal("30000.00"), 12),
        ],
    },
    {
        "name": "Ring Light 18-Inch with Tripod",
        "description": "Professional 18-inch LED ring light with adjustable tripod stand and phone holder. 3 color modes, dimmable.",
        "price": Decimal("18000.00"),
        "sku": "GADG-004",
        "category": "Gadgets & Electronics",
        "tags": ["ring light", "tripod", "LED", "photography", "gadget", "content creator", "selfie", "video"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "18 inches", "type": "With Tripod"}, Decimal("18000.00"), 25),
            ({"size": "12 inches", "type": "With Tripod"}, Decimal("11000.00"), 35),
            ({"size": "18 inches", "type": "With Tripod + Remote"}, Decimal("20000.00"), 15),
        ],
    },
    {
        "name": "Portable Bluetooth Speaker",
        "description": "360-degree surround sound, waterproof IPX7. 12-hour playtime with deep bass. Built-in mic for calls.",
        "price": Decimal("16000.00"),
        "sku": "GADG-005",
        "category": "Gadgets & Electronics",
        "tags": ["speaker", "bluetooth", "portable", "music", "gadget", "audio", "waterproof", "bass"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1589003077984-894e133dabab?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1558089687-f282ffcbc126?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black"}, Decimal("16000.00"), 35),
            ({"color": "Red"}, Decimal("16000.00"), 20),
            ({"color": "Camouflage Green"}, Decimal("16500.00"), 15),
        ],
    },

    # ── BEAUTY & SKINCARE (5) ────────────────────────────────────
    {
        "name": "Glow Vitamin C Serum Set",
        "description": "3-piece vitamin C skincare set: cleanser, serum, and moisturizer. For brighter, even-toned skin.",
        "price": Decimal("18000.00"),
        "sku": "BEAU-001",
        "category": "Beauty & Skincare",
        "tags": ["skincare", "vitamin C", "serum", "beauty", "glow", "brightening", "face", "moisturizer", "cleanser"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1570194065650-d99fb4b38b17?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"skin_type": "Normal/Combination"}, Decimal("18000.00"), 30),
            ({"skin_type": "Oily/Acne-Prone"}, Decimal("18500.00"), 25),
            ({"skin_type": "Dry/Sensitive"}, Decimal("19000.00"), 20),
        ],
    },
    {
        "name": "Matte Liquid Lipstick Collection",
        "description": "Long-lasting matte liquid lipstick. Transfer-proof, lightweight formula. Set of 6 shades.",
        "price": Decimal("11000.00"),
        "sku": "BEAU-002",
        "category": "Beauty & Skincare",
        "tags": ["lipstick", "matte", "makeup", "beauty", "lip", "cosmetics", "women", "liquid lipstick"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1631214524020-7e18db9a8f92?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"shade": "Nude Collection (6 pcs)"}, Decimal("11000.00"), 40),
            ({"shade": "Bold Red Collection (6 pcs)"}, Decimal("11000.00"), 30),
            ({"shade": "Berry & Plum Collection (6 pcs)"}, Decimal("11000.00"), 25),
            ({"shade": "Mixed Favorites (6 pcs)"}, Decimal("12000.00"), 20),
        ],
    },
    {
        "name": "Shea Butter Body Cream (500ml)",
        "description": "100% organic shea butter body cream infused with honey and coconut oil. Deep moisturizing for all skin types.",
        "price": Decimal("5500.00"),
        "sku": "BEAU-003",
        "category": "Beauty & Skincare",
        "tags": ["shea butter", "body cream", "lotion", "beauty", "moisturizer", "skincare", "organic", "body"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1570194065650-d99fb4b38b17?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"scent": "Original Shea"}, Decimal("5500.00"), 60),
            ({"scent": "Lavender"}, Decimal("5800.00"), 40),
            ({"scent": "Coconut & Honey"}, Decimal("6000.00"), 35),
            ({"scent": "Unscented"}, Decimal("5500.00"), 30),
        ],
    },
    {
        "name": "Complete Makeup Brush Set",
        "description": "Professional 15-piece makeup brush set with vegan bristles and PU leather case.",
        "price": Decimal("14000.00"),
        "sku": "BEAU-004",
        "category": "Beauty & Skincare",
        "tags": ["makeup brush", "brush set", "beauty", "cosmetics", "makeup", "tools", "foundation brush"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Rose Gold"}, Decimal("14000.00"), 20),
            ({"color": "Black/Gold"}, Decimal("14000.00"), 25),
            ({"color": "Marble White"}, Decimal("15000.00"), 15),
        ],
    },
    {
        "name": "Oud Arabian Perfume Oil (50ml)",
        "description": "Luxurious concentrated oud perfume oil. Long-lasting 12+ hours, alcohol-free. Unisex fragrance.",
        "price": Decimal("9500.00"),
        "sku": "BEAU-005",
        "category": "Beauty & Skincare",
        "tags": ["perfume", "oud", "fragrance", "beauty", "arabian", "oil", "scent", "unisex", "cologne"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1557170334-a9632e77c6e4?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"variant": "Classic Oud"}, Decimal("9500.00"), 30),
            ({"variant": "Oud & Rose"}, Decimal("10000.00"), 25),
            ({"variant": "Oud & Musk"}, Decimal("10000.00"), 20),
            ({"variant": "Royal Oud (Premium)"}, Decimal("14000.00"), 10),
        ],
    },

    # ── HOME & KITCHEN (5) ───────────────────────────────────────
    {
        "name": "Non-Stick Cookware Set (10 pcs)",
        "description": "Premium granite-coated non-stick cookware set. Includes pots, frying pans, and lids. Works on all stove types.",
        "price": Decimal("38000.00"),
        "sku": "HOME-001",
        "category": "Home & Kitchen",
        "tags": ["cookware", "pots", "non-stick", "kitchen", "home", "cooking", "frying pan", "granite"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1584990347449-a6d49d5a8f6e?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black/Grey"}, Decimal("38000.00"), 15),
            ({"color": "Burgundy"}, Decimal("39000.00"), 12),
            ({"color": "Cream/Gold"}, Decimal("40000.00"), 8),
        ],
    },
    {
        "name": "Rechargeable Standing Fan 18-Inch",
        "description": "Solar-compatible rechargeable standing fan. 8-hour battery, remote control, 3 speed settings. NEPA-proof.",
        "price": Decimal("35000.00"),
        "sku": "HOME-002",
        "category": "Home & Kitchen",
        "tags": ["fan", "rechargeable", "standing fan", "home", "solar", "electric", "cooling", "NEPA"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1617375407633-acd67aba4464?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "White"}, Decimal("35000.00"), 20),
            ({"color": "Black"}, Decimal("35000.00"), 18),
            ({"color": "Blue"}, Decimal("36000.00"), 10),
        ],
    },
    {
        "name": "Luxury Bedsheet Set (6 pcs)",
        "description": "Egyptian cotton feel bedsheet set: fitted sheet, flat sheet, 4 pillowcases. 300 thread count.",
        "price": Decimal("22000.00"),
        "sku": "HOME-003",
        "category": "Home & Kitchen",
        "tags": ["bedsheet", "bedding", "home", "bedroom", "cotton", "luxury", "pillowcase", "bed"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1616627561950-9f746e330187?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"size": "King", "color": "White"}, Decimal("22000.00"), 20),
            ({"size": "Queen", "color": "White"}, Decimal("18000.00"), 25),
            ({"size": "King", "color": "Grey"}, Decimal("22000.00"), 15),
            ({"size": "King", "color": "Navy Blue"}, Decimal("22500.00"), 12),
            ({"size": "Queen", "color": "Blush Pink"}, Decimal("18500.00"), 18),
        ],
    },
    {
        "name": "Insulated Food Flask (800ml)",
        "description": "Stainless steel vacuum insulated food flask. Keeps food hot for 12 hours. Leak-proof lid.",
        "price": Decimal("9000.00"),
        "sku": "HOME-004",
        "category": "Home & Kitchen",
        "tags": ["food flask", "flask", "thermos", "insulated", "kitchen", "home", "stainless steel", "lunch"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1570649236871-1aac57b4091c?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1610824224972-db9c5be63b00?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Silver"}, Decimal("9000.00"), 40),
            ({"color": "Rose Gold"}, Decimal("9500.00"), 30),
            ({"color": "Matte Black"}, Decimal("9500.00"), 25),
        ],
    },
    {
        "name": "LED Rechargeable Desk Lamp",
        "description": "Touch-control LED desk lamp with 3 brightness levels. USB charging port. Foldable design. Eye-care technology.",
        "price": Decimal("8000.00"),
        "sku": "HOME-005",
        "category": "Home & Kitchen",
        "tags": ["desk lamp", "LED", "lamp", "home", "office", "rechargeable", "light", "study"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1507473885765-e6ed057ab6fe?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1534353436294-0dbd4bdac845?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "White"}, Decimal("8000.00"), 35),
            ({"color": "Black"}, Decimal("8000.00"), 30),
            ({"color": "Pink"}, Decimal("8500.00"), 20),
        ],
    },

    # ── BAGS & ACCESSORIES (5) ───────────────────────────────────
    {
        "name": "Leather Tote Handbag",
        "description": "Genuine leather tote bag with inner zip compartment and detachable strap. Spacious and elegant.",
        "price": Decimal("28000.00"),
        "sku": "BAGS-001",
        "category": "Bags & Accessories",
        "tags": ["handbag", "tote", "leather", "bag", "women", "fashion", "purse", "accessories"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1584917865735-30a500e5ee93?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1591561954557-26941169b49e?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Brown"}, Decimal("28000.00"), 15),
            ({"color": "Black"}, Decimal("28000.00"), 20),
            ({"color": "Burgundy"}, Decimal("29000.00"), 12),
            ({"color": "Cream"}, Decimal("29000.00"), 10),
        ],
    },
    {
        "name": "Stainless Steel Wrist Watch",
        "description": "Classic unisex stainless steel wrist watch. Water-resistant 30m. Japanese quartz movement.",
        "price": Decimal("18000.00"),
        "sku": "BAGS-002",
        "category": "Bags & Accessories",
        "tags": ["watch", "wrist watch", "stainless steel", "accessories", "unisex", "fashion", "timepiece"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1522312346375-d1a52e2b99b3?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1533139502658-0198f920d8e8?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Silver/White Dial"}, Decimal("18000.00"), 20),
            ({"color": "Gold/Black Dial"}, Decimal("19000.00"), 15),
            ({"color": "Rose Gold/Pink Dial"}, Decimal("19000.00"), 12),
            ({"color": "Black/Green Dial"}, Decimal("18500.00"), 18),
        ],
    },
    {
        "name": "Laptop Backpack (USB Port)",
        "description": "Water-resistant laptop backpack with built-in USB charging port. Fits up to 15.6-inch laptops. Anti-theft design.",
        "price": Decimal("15000.00"),
        "sku": "BAGS-003",
        "category": "Bags & Accessories",
        "tags": ["backpack", "laptop bag", "bag", "USB", "school", "office", "travel", "accessories"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1581605405669-fcdf81165afa?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1622560480654-d96214fddae9?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"color": "Black"}, Decimal("15000.00"), 30),
            ({"color": "Grey"}, Decimal("15000.00"), 25),
            ({"color": "Navy Blue"}, Decimal("15500.00"), 18),
        ],
    },
    {
        "name": "Gold-Plated Jewelry Set (4 pcs)",
        "description": "Elegant gold-plated jewelry set: necklace, earrings, bracelet, and ring. Hypoallergenic. Gift boxed.",
        "price": Decimal("12000.00"),
        "sku": "BAGS-004",
        "category": "Bags & Accessories",
        "tags": ["jewelry", "gold", "necklace", "earrings", "bracelet", "ring", "accessories", "women", "gift"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1515562141589-67f0d569b44e?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"style": "Classic Chain"}, Decimal("12000.00"), 25),
            ({"style": "Cuban Link"}, Decimal("13000.00"), 20),
            ({"style": "Butterfly Pendant"}, Decimal("13500.00"), 15),
            ({"style": "Layered Minimalist"}, Decimal("12500.00"), 18),
        ],
    },
    {
        "name": "Designer Sunglasses (UV400)",
        "description": "Premium UV400 polarized sunglasses with branded hard case. Multiple frame styles available.",
        "price": Decimal("9000.00"),
        "sku": "BAGS-005",
        "category": "Bags & Accessories",
        "tags": ["sunglasses", "UV400", "shades", "accessories", "fashion", "eyewear", "polarized", "unisex"],
        "media": [
            {"url": "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&h=600&fit=crop", "type": "image"},
            {"url": "https://images.unsplash.com/photo-1473496169904-658ba7c44d8a?w=600&h=600&fit=crop", "type": "image"},
        ],
        "variants": [
            ({"frame": "Aviator", "color": "Gold/Brown"}, Decimal("9000.00"), 20),
            ({"frame": "Cat Eye", "color": "Black"}, Decimal("9000.00"), 25),
            ({"frame": "Round", "color": "Tortoise"}, Decimal("9500.00"), 15),
            ({"frame": "Oversized Square", "color": "Black/Gold"}, Decimal("10000.00"), 12),
        ],
    },
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
            for p_data in PRODUCTS:
                result = await db.execute(
                    select(Product).filter(Product.sku == p_data["sku"])
                )
                existing = result.scalars().first()
                if existing:
                    existing.media = p_data["media"]
                    existing.tags = p_data["tags"]
                    existing.price = p_data["price"]
                    existing.description = p_data["description"]
                    print(f"  Updated '{p_data['name']}' (SKU: {p_data['sku']})")
                    created += 1
                    continue

                product = Product(
                    tracking_id=generate_tracking_id(p_data["name"]),
                    name=p_data["name"],
                    description=p_data["description"],
                    price=p_data["price"],
                    sku=p_data["sku"],
                    category_id=cat_map.get(p_data["category"]),
                    media=p_data["media"],
                    tags=p_data["tags"],
                    is_active=True,
                )
                db.add(product)
                await db.flush()

                for attrs, v_price, inv_qty in p_data["variants"]:
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
                print(f"  Created product: {p_data['name']} ({len(p_data['variants'])} variants)")

            await db.commit()
            print(
                f"\nDone! Seeded {created} products across {len(CATEGORIES)} categories."
            )

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
