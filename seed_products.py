"""
Seed script: populates the database with 30 products across 6 categories.
Each product has at least 5 media items (images + videos) and variants with inventory.

Usage:
    python seed_products.py
"""

import random
import string
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import config directly to avoid circular imports
from app.core.config import Config

engine = create_engine(Config.CONNECTION_STRING, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.db.model.category_model import Category
from app.db.model.product_model import Product
from app.db.model.product_variant_model import ProductVariant


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
]


def make_media(product_slug: str) -> list[dict]:
    """Generate 5-6 media items: 5 images + any available videos."""
    media = []
    # 5 images
    for i in range(1, 6):
        media.append({
            "url": f"https://picsum.photos/seed/{product_slug}{i}/600/600",
            "type": "image",
        })
    # Add videos if available (use Cloudinary URLs in production)
    if SAMPLE_VIDEOS:
        num_videos = random.randint(1, min(2, len(SAMPLE_VIDEOS)))
        chosen_videos = random.sample(SAMPLE_VIDEOS, num_videos)
        for url in chosen_videos:
            media.append({
                "url": url,
                "type": "video",
            })
    return media


# ---------------------------------------------------------------------------
# Product data: 30 products across 6 Nigerian commerce categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"name": "Fashion", "description": "Clothing, shoes, and accessories"},
    {"name": "Hair & Wigs", "description": "Human hair, wigs, extensions, and hair accessories"},
    {"name": "Gadgets & Electronics", "description": "Phones, earbuds, chargers, and tech accessories"},
    {"name": "Beauty & Skincare", "description": "Skincare, makeup, fragrances, and body care"},
    {"name": "Home & Kitchen", "description": "Cookware, decor, bedding, and home essentials"},
    {"name": "Bags & Accessories", "description": "Handbags, jewelry, watches, and fashion accessories"},
]

# Each entry: (name, description, base_price, sku, category_name, variants)
# Variants: list of (attributes_dict, price, inventory)
PRODUCTS = [
    # ── FASHION (5) ──────────────────────────────────────────────
    (
        "Ankara Midi Dress",
        "Vibrant Ankara print midi dress with a flattering A-line silhouette. Perfect for owambe and casual outings.",
        Decimal("15000.00"), "FASH-001", "Fashion",
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
        Decimal("45000.00"), "FASH-002", "Fashion",
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
        Decimal("8500.00"), "FASH-003", "Fashion",
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
        Decimal("12000.00"), "FASH-004", "Fashion",
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
        Decimal("18000.00"), "FASH-005", "Fashion",
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
        Decimal("65000.00"), "HAIR-001", "Hair & Wigs",
        [
            ({"length": "16 inches", "color": "Natural Black"}, Decimal("65000.00"), 12),
            ({"length": "20 inches", "color": "Natural Black"}, Decimal("78000.00"), 10),
            ({"length": "24 inches", "color": "Natural Black"}, Decimal("92000.00"), 6),
            ({"length": "20 inches", "color": "#27 Honey Blonde"}, Decimal("82000.00"), 8),
            ({"length": "24 inches", "color": "#27 Honey Blonde"}, Decimal("95000.00"), 5),
        ],
    ),
    (
        "Bone Straight Bundles",
        "Grade 12A bone straight human hair bundles. Silky smooth, no shedding, no tangling.",
        Decimal("35000.00"), "HAIR-002", "Hair & Wigs",
        [
            ({"length": "14 inches", "bundles": "3 Bundles"}, Decimal("35000.00"), 20),
            ({"length": "18 inches", "bundles": "3 Bundles"}, Decimal("45000.00"), 15),
            ({"length": "22 inches", "bundles": "3 Bundles"}, Decimal("55000.00"), 10),
            ({"length": "18 inches", "bundles": "4 Bundles + Closure"}, Decimal("62000.00"), 8),
            ({"length": "22 inches", "bundles": "4 Bundles + Closure"}, Decimal("75000.00"), 5),
        ],
    ),
    (
        "Pixie Cut Short Wig",
        "Trendy pixie cut wig with adjustable straps. Lightweight, breathable cap construction.",
        Decimal("22000.00"), "HAIR-003", "Hair & Wigs",
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
        Decimal("8500.00"), "HAIR-004", "Hair & Wigs",
        [
            ({"length": "14 inches", "color": "1B Natural Black"}, Decimal("8500.00"), 40),
            ({"length": "18 inches", "color": "1B Natural Black"}, Decimal("9500.00"), 30),
            ({"length": "14 inches", "color": "T1B/30 Ombre"}, Decimal("9000.00"), 25),
            ({"length": "18 inches", "color": "T1B/27 Ombre"}, Decimal("10000.00"), 20),
        ],
    ),
    (
        "HD Lace Frontal 13x6",
        "Ultra-thin HD lace frontal closure. Invisible knots, melts into all skin tones.",
        Decimal("28000.00"), "HAIR-005", "Hair & Wigs",
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
        Decimal("18500.00"), "GADG-001", "Gadgets & Electronics",
        [
            ({"color": "Black"}, Decimal("18500.00"), 50),
            ({"color": "White"}, Decimal("18500.00"), 40),
            ({"color": "Navy Blue"}, Decimal("19000.00"), 25),
        ],
    ),
    (
        "20000mAh Power Bank",
        "Fast-charging power bank with USB-C and dual USB-A ports. LED display shows battery level.",
        Decimal("12000.00"), "GADG-002", "Gadgets & Electronics",
        [
            ({"color": "Black"}, Decimal("12000.00"), 60),
            ({"color": "White"}, Decimal("12000.00"), 45),
            ({"color": "Blue"}, Decimal("12500.00"), 30),
        ],
    ),
    (
        "Smart Watch Fitness Tracker",
        "Heart rate monitor, sleep tracking, SpO2 sensor. Water-resistant with 7-day battery life.",
        Decimal("25000.00"), "GADG-003", "Gadgets & Electronics",
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
        Decimal("15000.00"), "GADG-004", "Gadgets & Electronics",
        [
            ({"size": "18 inches", "type": "With Tripod"}, Decimal("15000.00"), 25),
            ({"size": "12 inches", "type": "With Tripod"}, Decimal("9500.00"), 35),
            ({"size": "18 inches", "type": "With Tripod + Remote"}, Decimal("17000.00"), 15),
        ],
    ),
    (
        "Portable Bluetooth Speaker",
        "360-degree surround sound, waterproof IPX7. 12-hour playtime with deep bass.",
        Decimal("14000.00"), "GADG-005", "Gadgets & Electronics",
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
        Decimal("16000.00"), "BEAU-001", "Beauty & Skincare",
        [
            ({"skin_type": "Normal/Combination"}, Decimal("16000.00"), 30),
            ({"skin_type": "Oily/Acne-Prone"}, Decimal("16500.00"), 25),
            ({"skin_type": "Dry/Sensitive"}, Decimal("17000.00"), 20),
        ],
    ),
    (
        "Matte Liquid Lipstick Collection",
        "Long-lasting matte liquid lipstick. Transfer-proof, lightweight formula. Set of 6 shades.",
        Decimal("9500.00"), "BEAU-002", "Beauty & Skincare",
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
        Decimal("4500.00"), "BEAU-003", "Beauty & Skincare",
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
        Decimal("12000.00"), "BEAU-004", "Beauty & Skincare",
        [
            ({"color": "Rose Gold"}, Decimal("12000.00"), 20),
            ({"color": "Black/Gold"}, Decimal("12000.00"), 25),
            ({"color": "Marble White"}, Decimal("13000.00"), 15),
        ],
    ),
    (
        "Oud Arabian Perfume Oil (50ml)",
        "Luxurious concentrated oud perfume oil. Long-lasting, alcohol-free. Unisex fragrance.",
        Decimal("8000.00"), "BEAU-005", "Beauty & Skincare",
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
        Decimal("32000.00"), "HOME-001", "Home & Kitchen",
        [
            ({"color": "Black/Grey"}, Decimal("32000.00"), 15),
            ({"color": "Burgundy"}, Decimal("33000.00"), 12),
            ({"color": "Cream/Gold"}, Decimal("34000.00"), 8),
        ],
    ),
    (
        "Rechargeable Standing Fan 18-Inch",
        "Solar-compatible rechargeable standing fan. 8-hour battery, remote control, 3 speed settings.",
        Decimal("28000.00"), "HOME-002", "Home & Kitchen",
        [
            ({"color": "White"}, Decimal("28000.00"), 20),
            ({"color": "Black"}, Decimal("28000.00"), 18),
            ({"color": "Blue"}, Decimal("29000.00"), 10),
        ],
    ),
    (
        "Luxury Bedsheet Set (6 pcs)",
        "Egyptian cotton feel bedsheet set: fitted sheet, flat sheet, 4 pillowcases. 300 thread count.",
        Decimal("18000.00"), "HOME-003", "Home & Kitchen",
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
        Decimal("7500.00"), "HOME-004", "Home & Kitchen",
        [
            ({"color": "Silver"}, Decimal("7500.00"), 40),
            ({"color": "Rose Gold"}, Decimal("8000.00"), 30),
            ({"color": "Matte Black"}, Decimal("8000.00"), 25),
        ],
    ),
    (
        "LED Rechargeable Desk Lamp",
        "Touch-control LED desk lamp with 3 brightness levels. USB charging port. Foldable design.",
        Decimal("6500.00"), "HOME-005", "Home & Kitchen",
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
        Decimal("22000.00"), "BAGS-001", "Bags & Accessories",
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
        Decimal("15000.00"), "BAGS-002", "Bags & Accessories",
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
        Decimal("12500.00"), "BAGS-003", "Bags & Accessories",
        [
            ({"color": "Black"}, Decimal("12500.00"), 30),
            ({"color": "Grey"}, Decimal("12500.00"), 25),
            ({"color": "Navy Blue"}, Decimal("13000.00"), 18),
        ],
    ),
    (
        "Gold-Plated Jewelry Set (4 pcs)",
        "Elegant gold-plated jewelry set: necklace, earrings, bracelet, and ring. Hypoallergenic.",
        Decimal("9500.00"), "BAGS-004", "Bags & Accessories",
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
        Decimal("7500.00"), "BAGS-005", "Bags & Accessories",
        [
            ({"frame": "Aviator", "color": "Gold/Brown"}, Decimal("7500.00"), 20),
            ({"frame": "Cat Eye", "color": "Black"}, Decimal("7500.00"), 25),
            ({"frame": "Round", "color": "Tortoise"}, Decimal("8000.00"), 15),
            ({"frame": "Oversized Square", "color": "Black/Gold"}, Decimal("8500.00"), 12),
        ],
    ),
]


def seed():
    db = SessionLocal()
    try:
        # ── 1. Create categories ────────────────────────────────
        cat_map = {}
        for cat_data in CATEGORIES:
            existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
            if existing:
                cat_map[cat_data["name"]] = existing.id
                print(f"  Category '{cat_data['name']}' already exists, skipping.")
            else:
                cat = Category(name=cat_data["name"], description=cat_data["description"])
                db.add(cat)
                db.flush()
                cat_map[cat_data["name"]] = cat.id
                print(f"  Created category: {cat_data['name']}")

        # ── 2. Create products + variants ───────────────────────
        created = 0
        for name, desc, price, sku, cat_name, variants in PRODUCTS:
            existing = db.query(Product).filter(Product.sku == sku).first()
            if existing:
                # Update media with new images + videos
                slug = sku.lower().replace("-", "")
                existing.media = make_media(slug)
                print(f"  Updated media for '{name}' (SKU: {sku})")
                created += 1
                continue

            slug = sku.lower().replace("-", "")
            product = Product(
                tracking_id=generate_tracking_id(name),
                name=name,
                description=desc,
                price=price,
                sku=sku,
                category_id=cat_map.get(cat_name),
                media=make_media(slug),
                is_active=True,
            )
            db.add(product)
            db.flush()

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

        db.commit()
        print(f"\nDone! Seeded {created} new products across {len(CATEGORIES)} categories.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
