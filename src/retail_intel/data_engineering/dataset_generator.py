"""Enterprise Dataset Engine: Generates dynamic synthetic retail catalogs and ingests real-world e-commerce data."""

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from retail_intel.core.logging import get_logger

logger = get_logger("data_engineering.dataset_generator")

CATEGORIES_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "Consumer Electronics": {
        "subcategories": ["Audio & Sound", "Television & Video", "Smartphones & Tablets", "Smart Home IoT", "Computing & Laptops"],
        "oems": [
            {"id": "OEM-AUDIO-SHENZHEN-88", "name": "Shenzhen Acoustic Fab", "region": "Shenzhen, CN"},
            {"id": "OEM-DISPLAYS-KOREA-12", "name": "Gumi Precision Displays", "region": "Gumi, KR"},
            {"id": "OEM-SEMICON-TAIWAN-03", "name": "Hsinchu Microelectronics", "region": "Hsinchu, TW"},
            {"id": "OEM-OPTICS-JAPAN-09", "name": "Kyoto Precision Optics", "region": "Kyoto, JP"},
        ],
        "products": [
            ("AuraWave Pro Wireless Noise-Cancelling Headphones", 349.99, 140.00, "count", 1, -1.45),
            ("VortexView 65-Inch 4K OLED HDR Smart TV", 1999.99, 950.00, "count", 1, -2.10),
            ("Horizon CinemaBeam 4K Laser Projector", 1499.00, 700.00, "count", 1, -1.80),
            ("AuraStream Ultra HD Soundbar with Subwoofer", 499.99, 210.00, "count", 1, -1.25),
            ("Zenith Pulse ANC Earbuds Waterproof", 179.99, 65.00, "count", 1, -1.60),
            ("Apex UltraBook Pro 15-inch M3 Laptop", 1899.00, 1100.00, "count", 1, -1.95),
            ("Vortex Tab 11-inch AMOLED Tablet 256GB", 699.00, 320.00, "count", 1, -1.50),
            ("QuantumLink Mesh WiFi 7 Router Tri-Band", 399.00, 160.00, "count", 1, -1.15),
            ("ApexVision 34-Inch Curved Ultrawide Monitor 165Hz", 799.00, 380.00, "count", 1, -1.75),
            ("AuraCharge 100W GaN Fast Multi-Port Charger", 79.99, 24.00, "count", 1, -0.90),
        ],
    },
    "Home & Living": {
        "subcategories": ["Office Chairs", "Standing Desks", "Living Room Seating", "Ergonomic Accessories", "Modern Lighting"],
        "oems": [
            {"id": "OEM-FURN-DONGGUAN-99", "name": "Dongguan Ergonomic Mechanics", "region": "Dongguan, CN"},
            {"id": "OEM-WOOD-VIETNAM-22", "name": "Binh Duong Woodcrafts", "region": "Binh Duong, VN"},
            {"id": "OEM-STEEL-POLAND-15", "name": "Silesia Steel Furniture", "region": "Katowice, PL"},
        ],
        "products": [
            ("ErgoSpine Executive Mesh Ergonomic Office Chair", 499.00, 210.00, "count", 1, -1.10),
            ("NovaComfort Dual-Motor Electric Standing Desk", 649.00, 280.00, "count", 1, -1.35),
            ("ErgoRest Adjustable Lumbar Support Cushion", 59.99, 18.00, "count", 1, -0.85),
            ("AuraGlow Architect LED Desk Lamp with Wireless Charging", 89.99, 32.00, "count", 1, -0.95),
            ("NovaLuxe Modular Velvet Sectional Sofa", 1299.00, 520.00, "count", 1, -1.65),
            ("Solid Oak Scandinavian Dining Table 6-Seater", 899.00, 390.00, "count", 1, -1.20),
            ("AeroBreeze Smart Air Purifier HEPA H13", 249.00, 95.00, "count", 1, -1.40),
        ],
    },
    "Apparel & Fashion": {
        "subcategories": ["Athletic Footwear", "Outerwear & Jackets", "Activewear Performance", "Premium Denim", "Accessories"],
        "oems": [
            {"id": "OEM-TEXTILE-PORTUGAL-18", "name": "Porto Technical Fabrics", "region": "Porto, PT"},
            {"id": "OEM-SHOES-INDONESIA-41", "name": "Java Athletic Footwear Fab", "region": "Surabaya, ID"},
            {"id": "OEM-DENIM-TURKEY-08", "name": "Izmir Denim Mills", "region": "Izmir, TR"},
        ],
        "products": [
            ("AeroStep Breathable Carbon-Plated Running Shoes", 160.00, 55.00, "count", 1, -1.85),
            ("NordicShield 3-Layer All-Weather Mountain Jacket", 280.00, 105.00, "count", 1, -1.40),
            ("AeroFlex Ultra-Light Moisture Wicking Performance Tee", 45.00, 12.00, "count", 1, -1.20),
            ("ApexRaw Selvedge Slim-Taper Denim Jeans", 140.00, 48.00, "count", 1, -1.15),
            ("NordicTherma Merino Wool Baselayer Crew", 95.00, 32.00, "count", 1, -1.05),
            ("AeroTrail Waterproof Trail Running Shoes", 175.00, 62.00, "count", 1, -1.70),
        ],
    },
    "Grocery & Gourmet": {
        "subcategories": ["Specialty Coffee & Tea", "Artisan Pantry", "Healthy Snacks", "Organic Condiments", "Cold Beverages"],
        "oems": [
            {"id": "OEM-COFFEE-COLOMBIA-05", "name": "Medellin Highland Roasters", "region": "Medellin, CO"},
            {"id": "OEM-ORGANIC-OREGON-14", "name": "Pacific Bio-Organics", "region": "Oregon, US"},
            {"id": "OEM-TEA-JAPAN-02", "name": "Uji Heritage Green Teas", "region": "Kyoto, JP"},
        ],
        "products": [
            ("Aura Artisan Roast Whole Bean Single Origin Coffee 12oz", 18.99, 6.50, "oz", 12, -0.75),
            ("Highland Organic Matcha Ceremonial Grade 100g", 28.50, 9.20, "g", 100, -0.65),
            ("Pacific Cold-Pressed Extra Virgin Olive Oil 500ml", 22.00, 8.00, "ml", 500, -0.80),
            ("Peak Organic Raw Almond Butter 16oz", 14.99, 5.20, "oz", 16, -0.90),
            ("Highland Artisan Dark Chocolate Bars 72% Cacao 4-Pack", 16.00, 5.50, "count", 4, -0.70),
            ("Pacific Pure Raw Manuka Honey MGO 400+ 250g", 38.00, 14.50, "g", 250, -0.55),
        ],
    },
    "Tools & Hardware": {
        "subcategories": ["Cordless Power Drills", "Mechanics Tool Sets", "Heavy Duty Workbenches", "Measurement & Lasers"],
        "oems": [
            {"id": "OEM-TOOLS-GERMANY-07", "name": "Stuttgart Precision Tools", "region": "Stuttgart, DE"},
            {"id": "OEM-METALS-OHIO-55", "name": "Midwest Forging Works", "region": "Ohio, US"},
            {"id": "OEM-MOTORS-TAIWAN-33", "name": "Taichung Brushless Motors", "region": "Taichung, TW"},
        ],
        "products": [
            ("TitanForce 20V Max Brushless Cordless Drill Kit", 149.00, 62.00, "count", 1, -1.30),
            ("TitanPro Heavy Duty 120-Piece Mechanics Tool Set", 199.00, 78.00, "count", 1, -1.05),
            ("Stuttgart Professional Rotary Hammer Drill SDS-Plus", 279.00, 115.00, "count", 1, -1.25),
            ("TitanBeam 360-Degree Self-Leveling Green Laser Level", 129.00, 48.00, "count", 1, -1.15),
            ("TitanForge Steel Garage Heavy Duty Workbench 72in", 699.00, 310.00, "count", 1, -1.45),
        ],
    },
    "Beauty & Personal Care": {
        "subcategories": ["Skincare Serums", "Haircare Tech", "Clean Cosmetics", "Men's Grooming", "Fragrance"],
        "oems": [
            {"id": "OEM-COSMETICS-FRANCE-04", "name": "Grasse Botanical Laboratories", "region": "Grasse, FR"},
            {"id": "OEM-SKINCARE-KOREA-27", "name": "Seoul Derma Formulation Lab", "region": "Seoul, KR"},
        ],
        "products": [
            ("Lumière Hydra-Plump Hyaluronic Acid Serum 30ml", 68.00, 14.00, "ml", 30, -0.85),
            ("AuraSonic Ionic High-Speed Hair Dryer 110k RPM", 189.00, 65.00, "count", 1, -1.50),
            ("Lumière Peptide Age-Defying Night Cream 50ml", 84.00, 19.00, "ml", 50, -0.70),
            ("TitanGroom Pro All-in-One Beard & Body Trimmer", 79.00, 26.00, "count", 1, -1.20),
        ],
    },
    "Sports & Outdoors": {
        "subcategories": ["Camping & Hiking", "Cycling & Gear", "Water Sports", "Fitness Equipment"],
        "oems": [
            {"id": "OEM-OUTDOOR-COLORADO-19", "name": "Rocky Mountain Gearworks", "region": "Colorado, US"},
            {"id": "OEM-POLYMER-TAIWAN-52", "name": "Formosa Composite Polymer", "region": "Kaohsiung, TW"},
        ],
        "products": [
            ("AlpineApex Ultralight 2-Person Backpacking Tent", 299.00, 115.00, "count", 1, -1.40),
            ("HydroGlide Inflatable Stand-Up Paddleboard Kit 11ft", 449.00, 180.00, "count", 1, -1.75),
            ("VortexPulse Smart Indoor Magnetic Exercise Bike", 899.00, 390.00, "count", 1, -1.90),
            ("AlpineTrail 65L Internal Frame Expedition Backpack", 219.00, 82.00, "count", 1, -1.15),
        ],
    },
    "Toys & Hobbies": {
        "subcategories": ["STEM Building Kits", "RC Vehicles", "Board Games & Puzzles", "Educational Tech"],
        "oems": [
            {"id": "OEM-TOYS-DENMARK-11", "name": "Billund Modular Bricks", "region": "Billund, DK"},
            {"id": "OEM-RC-SHENZHEN-64", "name": "Bay Area Micro Drones", "region": "Shenzhen, CN"},
        ],
        "products": [
            ("RoboCraft Advanced STEM Programmable Robotics Kit", 139.00, 48.00, "count", 1, -1.30),
            ("AeroFalcon 4K GPS Brushless Camera Drone", 299.00, 120.00, "count", 1, -1.65),
            ("GalaxyQuest Epic Strategy Tabletop Board Game", 79.99, 24.00, "count", 1, -0.90),
        ],
    },
    "Health & Wellness": {
        "subcategories": ["Vitamins & Supplements", "Recovery & Massage", "Sleep Tech", "Hydration Tracking"],
        "oems": [
            {"id": "OEM-NUTRITION-UTAH-81", "name": "Wasatch Nutra Science", "region": "Utah, US"},
            {"id": "OEM-WELLNESS-SWISS-06", "name": "Zurich Biometrics AG", "region": "Zurich, CH"},
        ],
        "products": [
            ("AuraThera Deep Tissue Percussive Massage Gun", 199.00, 68.00, "count", 1, -1.45),
            ("VitalCore Plant-Based Clean Protein Isolate 2lb", 44.99, 15.00, "oz", 32, -0.80),
            ("SomnaRest Smart Sleep Eye Mask with Soundscape", 89.00, 28.00, "count", 1, -1.10),
        ],
    },
    "Automotive Accessories": {
        "subcategories": ["Dash Cams & Electronics", "Detailing & Care", "Interior Organizers", "Tire & Emergency"],
        "oems": [
            {"id": "OEM-AUTOTECH-GERMANY-44", "name": "Bavaria Automotive Sensors", "region": "Munich, DE"},
            {"id": "OEM-PLASTICS-MICHIGAN-16", "name": "Detroit Auto Moldings", "region": "Michigan, US"},
        ],
        "products": [
            ("ApexCam Dual 4K Front and Rear Dash Camera GPS", 179.00, 64.00, "count", 1, -1.35),
            ("TitanInflate Portable Cordless Auto Tire Inflator 150PSI", 69.99, 22.00, "count", 1, -1.10),
            ("AutoShine Ceramic Graphene Spray Coating 16oz", 34.99, 9.50, "oz", 16, -0.85),
        ],
    },
}

# 48 Distinct Competitors Across 4 Market Tiers
COMPETITORS_POOL: List[Tuple[str, str, str, str]] = [
    # Tier 1: Mega Big-Box & Mass Merchants
    ("COMP-AMZ", "Amazon", "amazon.com", "Big Box E-Commerce"),
    ("COMP-WMT", "Walmart", "walmart.com", "Omnichannel Superstore"),
    ("COMP-TGT", "Target", "target.com", "Omnichannel Department"),
    ("COMP-CSTC", "Costco Wholesale", "costco.com", "Wholesale Club"),
    ("COMP-BBY", "Best Buy", "bestbuy.com", "Electronics Specialist"),
    ("COMP-HD", "The Home Depot", "homedepot.com", "Home Improvement"),
    ("COMP-LOW", "Lowe's", "lowes.com", "Home Improvement"),
    ("COMP-KRGR", "Kroger", "kroger.com", "Supermarket Grocery"),
    ("COMP-MCY", "Macy's", "macys.com", "Department Store"),
    ("COMP-KHL", "Kohl's", "kohls.com", "Department Store"),
    # Tier 2: Specialized E-Commerce & Category Giants
    ("COMP-WAYF", "Wayfair", "wayfair.com", "Home & Furniture"),
    ("COMP-NEWE", "Newegg", "newegg.com", "Computing & Tech"),
    ("COMP-BHPH", "B&H Photo Video", "bhphotovideo.com", "Pro AV & Optics"),
    ("COMP-SPHR", "Sephora", "sephora.com", "Prestige Beauty"),
    ("COMP-ULTA", "Ulta Beauty", "ulta.com", "Beauty & Cosmetics"),
    ("COMP-CHWY", "Chewy", "chewy.com", "Pet Specialist"),
    ("COMP-REI", "REI Co-op", "rei.com", "Outdoor & Camping"),
    ("COMP-DKS", "Dick's Sporting Goods", "dickssportinggoods.com", "Sporting Goods"),
    ("COMP-ZARA", "Zara", "zara.com", "Fast Fashion"),
    ("COMP-ASOS", "ASOS", "asos.com", "Online Fashion"),
    ("COMP-NIKE", "Nike Direct", "nike.com", "Athletic Footwear & Apparel"),
    ("COMP-LULU", "Lululemon", "lululemon.com", "Activewear"),
    ("COMP-IKEA", "IKEA", "ikea.com", "Home Furnishing"),
    ("COMP-WWMS", "Williams-Sonoma", "williams-sonoma.com", "Gourmet Kitchen"),
    ("COMP-AUTZ", "AutoZone", "autozone.com", "Automotive Parts"),
    # Tier 3: High-Agility Dynamic Digital Retailers
    ("COMP-ZENITH", "ZenithMart", "zenithmart.example", "Agile Marketplace"),
    ("COMP-APEX", "ApexRetail", "apexretail.example", "Digital Pureplay"),
    ("COMP-NOVA", "NovaHome Direct", "novahome.example", "DTC Furniture"),
    ("COMP-TITAN", "TitanSupply Global", "titansupply.example", "Industrial Hardware"),
    ("COMP-NORDIC", "NordicGear Outdoor", "nordicgear.example", "Specialty Outdoor"),
    ("COMP-CYBER", "CyberMarket Inc", "cybermarket.example", "Electronics Outlet"),
    ("COMP-PRIME", "PrimeCart Express", "primecart.example", "Discount E-Commerce"),
    ("COMP-OMNI", "OmniGoods Superstore", "omnigoods.example", "Multi-Category Discounter"),
    ("COMP-VAULT", "GlobalVault Direct", "globalvault.example", "Wholesale Liquidator"),
    ("COMP-URBAN", "UrbanTrade Brands", "urbantrade.example", "Modern Apparel"),
    ("COMP-METRO", "MetroDeals Online", "metrodeals.example", "Flash Sale Site"),
    ("COMP-HYPER", "HyperOutlet", "hyperoutlet.example", "Deep Discount"),
    ("COMP-QUICK", "QuickShip Prime", "quickship.example", "Fast Fulfillment"),
    ("COMP-PEAK", "PeakMerchandise", "peakmerch.example", "Apparel & Gear"),
    ("COMP-HORIZ", "HorizonDeals", "horizondeals.example", "Consumer Electronics"),
    ("COMP-FRONT", "FrontierRetail", "frontierretail.example", "Tools & Hardware"),
    ("COMP-STELL", "StellarShop DTC", "stellarshop.example", "Direct-to-Consumer"),
    ("COMP-VANGU", "VanguardStore", "vanguardstore.example", "Omnichannel Direct"),
    ("COMP-QUANT", "QuantumDirect", "quantumdirect.example", "Tech Innovations"),
    ("COMP-NEXUS", "NexusGoods Corp", "nexusgoods.example", "Home & Office"),
    ("COMP-CREST", "CrestMart Global", "crestmart.example", "Everyday Value"),
    ("COMP-SUMMIT", "SummitSupply Co", "summitsupply.example", "Outdoor Hardware"),
    ("COMP-AURORA", "AuroraRetail Brands", "auroraretail.example", "Beauty & Lifestyle"),
]


def generate_gtin14(seed_num: int) -> str:
    """Generates a valid GTIN-14 string with a computed Modulo-10 check digit."""
    base_13 = f"00840080{seed_num:05d}"
    weights = [3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]
    total = sum(int(digit) * w for digit, w in zip(base_13, weights))
    check_digit = (10 - (total % 10)) % 10
    return f"{base_13}{check_digit}"


class DatasetGenerator:
    """Generates parameterized synthetic or realistic enterprise retail catalogs with 20,000+ data points."""

    def __init__(self, random_seed: int = 42):
        self.random = random.Random(random_seed)

    def generate_enterprise_catalogs(
        self, target_sku_count: int = 24
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generates matching internal and competitor catalogs across 10 categories and 48 competitors."""
        internal_catalog: List[Dict[str, Any]] = []
        competitor_catalog: List[Dict[str, Any]] = []

        categories = list(CATEGORIES_TAXONOMY.keys())

        for idx in range(1, target_sku_count + 1):
            cat_name = categories[idx % len(categories)]
            cat_data = CATEGORIES_TAXONOMY[cat_name]
            prod_template = cat_data["products"][idx % len(cat_data["products"])]
            oem = cat_data["oems"][idx % len(cat_data["oems"])]

            title_base, retail_price, cogs, unit_measure, pack_size, elasticity = prod_template
            brand_name = title_base.split()[0]
            gtin = generate_gtin14(idx)

            # 1. Internal Product Record
            int_sku = f"INT-{cat_name[:3].upper()}-{idx:03d}"
            target_margin = round((retail_price - cogs) / retail_price, 4)
            internal_item = {
                "sku": int_sku,
                "gtin": gtin,
                "title": f"{title_base} (Series {idx:02d})",
                "brand": brand_name,
                "canonical_category": f"{cat_name} > {cat_data['subcategories'][idx % len(cat_data['subcategories'])]}",
                "current_price": round(retail_price, 2),
                "cost_of_goods": round(cogs, 2),
                "margin_floor": round(cogs * 1.15, 2),
                "target_gross_margin_pct": target_margin,
                "price_elasticity": elasticity,
                "map_policy_price": round(retail_price * 0.95, 2),
                "weekly_velocity_units": self.random.randint(80, 1200),
                "unit_measure": unit_measure,
                "pack_size": pack_size,
                "specifications": {
                    "oem_factory_id": oem["id"],
                    "oem_factory_name": oem["name"],
                    "oem_region": oem["region"],
                    "warranty_months": 24,
                },
                "image_url": f"/static/images/prod_{int_sku.lower()}.jpg",
            }
            internal_catalog.append(internal_item)

            # 2. Competitor Product Record across 48 competitors
            comp_id, comp_name, comp_domain, comp_tier = COMPETITORS_POOL[idx % len(COMPETITORS_POOL)]
            comp_sku = f"{comp_id.split('-')[1]}-{cat_name[:3].upper()}-{idx:03d}"

            challenge_type = self.random.choice([
                "EXACT_GTIN",
                "DYNAMIC_COUPON",
                "DECEPTIVE_MULTIPACK",
                "PRIVATE_LABEL_OEM",
                "PHANTOM_STOCK",
                "HONEYPOT_TRAP",
                "MULTIMODAL_CLASH",
                "MAP_VIOLATION",
                "STANDARD_MATCH",
            ])

            base_price = round(retail_price * self.random.uniform(0.90, 1.05), 2)
            coupon = 0.0
            cart_discount = 0.0
            stock_status = "IN_STOCK"
            latency = self.random.randint(1, 3)
            is_honeypot = False
            is_phantom = False
            comp_title = f"{title_base} (Series {idx:02d})"
            comp_gtin = gtin
            comp_specs = dict(internal_item["specifications"])

            if challenge_type == "EXACT_GTIN":
                base_price = round(retail_price * 0.94, 2)
            elif challenge_type == "DYNAMIC_COUPON":
                coupon = round(base_price * 0.10, 2)
                cart_discount = round(base_price * 0.05, 2)
                comp_gtin = ""
            elif challenge_type == "DECEPTIVE_MULTIPACK":
                comp_title = f"{title_base} - 3 Pack Value Bundle"
                base_price = round(retail_price * 1.05, 2)
                comp_specs["deceptive_multipack"] = True
            elif challenge_type == "PRIVATE_LABEL_OEM":
                comp_title = f"{comp_name} Signature {title_base.split()[-2]} {title_base.split()[-1]}"
                base_price = round(retail_price * 0.80, 2)
                comp_gtin = ""
            elif challenge_type == "PHANTOM_STOCK":
                base_price = round(retail_price * 0.50, 2)
                stock_status = "BACKORDER"
                latency = 45
                is_phantom = True
            elif challenge_type == "HONEYPOT_TRAP":
                base_price = round(retail_price * 0.40, 2)
                is_honeypot = True
            elif challenge_type == "MULTIMODAL_CLASH":
                comp_title = f"{title_base} (2026 Edition)"
                comp_specs["chassis_year"] = 2024
            elif challenge_type == "MAP_VIOLATION":
                base_price = round(internal_item["map_policy_price"] * 0.88, 2)

            final_effective = max(0.01, round(base_price - coupon - cart_discount, 2))

            comp_item = {
                "competitor_id": comp_id,
                "competitor_name": comp_name,
                "competitor_domain": comp_domain,
                "competitor_tier": comp_tier,
                "competitor_sku": comp_sku,
                "target_internal_sku": int_sku,
                "gtin": comp_gtin,
                "title": comp_title,
                "brand": comp_name if challenge_type == "PRIVATE_LABEL_OEM" else brand_name,
                "raw_category": f"Store > {cat_name} > {cat_data['subcategories'][idx % len(cat_data['subcategories'])]}",
                "scraped_base_price": base_price,
                "on_page_coupon": coupon,
                "cart_discount": cart_discount,
                "final_effective_price": final_effective,
                "unit_measure": unit_measure,
                "pack_size": pack_size,
                "stock_status": stock_status,
                "fulfillment_latency_days": latency,
                "pdp_url": f"https://{comp_domain}/pdp/{comp_sku.lower()}",
                "image_url": f"/static/images/comp_{comp_sku.lower()}.jpg",
                "specifications": comp_specs,
                "customer_reviews_summary": "Customer verified authentic shipment.",
                "is_honeypot": is_honeypot,
                "is_phantom_stock": is_phantom,
                "challenge_class": challenge_type,
            }
            competitor_catalog.append(comp_item)

        return internal_catalog, competitor_catalog

    def generate_large_scale_dataset(
        self, total_datapoints: int = 20000
    ) -> Dict[str, Any]:
        """Generates 20,000+ data points including catalog SKUs, time-series observations, and pricing histories."""
        sku_count = max(48, min(500, total_datapoints // 40))
        internal_catalog, competitor_catalog = self.generate_enterprise_catalogs(sku_count)

        observations: List[Dict[str, Any]] = []
        now_ts = int(time.time())
        day_seconds = 86400

        # Generate time-series historical observations across 48 competitors and 30 days
        obs_needed = total_datapoints - len(internal_catalog) - len(competitor_catalog)
        obs_per_sku = max(1, obs_needed // len(competitor_catalog))

        obs_counter = 1
        for comp_item in competitor_catalog:
            base_p = comp_item["final_effective_price"]
            for step in range(obs_per_sku):
                days_ago = (step % 30)
                ts = now_ts - (days_ago * day_seconds)
                price_jitter = round(base_p * self.random.uniform(0.95, 1.05), 2)
                stock = "OUT_OF_STOCK" if (step == 0 and comp_item["is_phantom_stock"]) else ("IN_STOCK" if self.random.random() > 0.08 else "LOW_STOCK")
                obs = {
                    "observation_id": f"OBS-{obs_counter:07d}",
                    "competitor_id": comp_item["competitor_id"],
                    "competitor_name": comp_item["competitor_name"],
                    "competitor_sku": comp_item["competitor_sku"],
                    "target_internal_sku": comp_item["target_internal_sku"],
                    "observed_price": price_jitter,
                    "stock_status": stock,
                    "timestamp": ts,
                    "date": time.strftime("%Y-%m-%d", time.gmtime(ts)),
                    "scrape_latency_ms": self.random.randint(120, 850),
                    "proxy_region": self.random.choice(["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]),
                }
                observations.append(obs)
                obs_counter += 1

        total_count = len(internal_catalog) + len(competitor_catalog) + len(observations)
        logger.info("Generated large-scale dataset", total_datapoints=total_count, competitors=len(COMPETITORS_POOL), categories=len(CATEGORIES_TAXONOMY))

        return {
            "total_datapoints": total_count,
            "competitors_count": len(COMPETITORS_POOL),
            "categories_count": len(CATEGORIES_TAXONOMY),
            "internal_catalog": internal_catalog,
            "competitor_catalog": competitor_catalog,
            "observations": observations,
            "competitors_universe": [
                {"id": c[0], "name": c[1], "domain": c[2], "tier": c[3]}
                for c in COMPETITORS_POOL
            ],
            "categories_universe": list(CATEGORIES_TAXONOMY.keys()),
        }


if __name__ == "__main__":
    generator = DatasetGenerator()
    dataset = generator.generate_large_scale_dataset(20000)
    print("Total Data Points Generated:", dataset["total_datapoints"])
    print("Competitors Count:", dataset["competitors_count"])
    print("Categories Count:", dataset["categories_count"])
