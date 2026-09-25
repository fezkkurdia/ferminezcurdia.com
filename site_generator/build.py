#!/usr/bin/env python3
"""
Static Site Generator for ferminezcurdia.com
Processes folder-drop galleries, generates optimized thumbnails and WebP images,
and outputs pure static HTML with PhotoSwipe v5 and a responsive Photocrati-inspired layout.
"""

import os
import sys
import json
import re
import shutil
import hashlib
from pathlib import Path
from PIL import Image, ImageOps

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
GALLERIES_DIR = CONTENT_DIR / "galleries"
HOME_SLIDES_DIR = CONTENT_DIR / "home_slides"
SITE_GENERATOR_DIR = BASE_DIR / "site_generator"
STATIC_SRC_DIR = SITE_GENERATOR_DIR / "static"
TEMPLATES_DIR = SITE_GENERATOR_DIR / "templates"
DIST_DIR = BASE_DIR / "dist"
CACHE_FILE = BASE_DIR / ".cache" / "images_cache.json"
METADATA_FILE = BASE_DIR / "existing_site_metadata.json"

# Settings
THUMB_HEIGHT = 360
DISPLAY_MAX_DIM = 2560  # Ultra-crisp 4K/Retina display resolution
JPG_QUALITY = 84
WEBP_QUALITY = 82

# Clean Title Formatter
def format_title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    # Remove leading numbering like 01_, 001-, etc.
    stem = re.sub(r'^\d+[\s_-]*', '', stem)
    # Replace dashes and underscores
    clean = re.sub(r'[\s_-]+', ' ', stem).strip()
    return clean

# Extract EXIF title if available
def get_exif_title(img: Image.Image) -> str:
    try:
        exif = img.getexif()
        if not exif:
            return ""
        # 0x010e = ImageDescription
        desc = exif.get(0x010e)
        if desc and isinstance(desc, str):
            return desc.strip()
    except Exception:
        pass
    return ""

def compute_file_hash(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]

class SiteBuilder:
    def __init__(self):
        self.cache = self.load_cache()
        self.metadata = self.load_metadata()
        self.galleries = []
        self.home_slides = []

    def load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_cache(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    def load_metadata(self) -> dict:
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def process_image(self, src_path: Path, dest_gallery_dir: Path):
        """Generates thumb and display versions in both JPG and WebP format."""
        file_hash = compute_file_hash(src_path)
        cache_key = f"{src_path.name}_{file_hash}_{DISPLAY_MAX_DIM}"

        thumb_dir = dest_gallery_dir / "thumbs"
        display_dir = dest_gallery_dir / "display"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        display_dir.mkdir(parents=True, exist_ok=True)

        stem = src_path.stem
        thumb_jpg = thumb_dir / f"{stem}.jpg"
        thumb_webp = thumb_dir / f"{stem}.webp"
        display_jpg = display_dir / f"{stem}.jpg"
        display_webp = display_dir / f"{stem}.webp"

        # Check if already cached and exists
        if cache_key in self.cache:
            c = self.cache[cache_key]
            if (thumb_jpg.exists() and thumb_webp.exists() and
                display_jpg.exists() and display_webp.exists()):
                return c

        # Process image
        with Image.open(src_path) as orig:
            # Auto-orient based on EXIF
            img = ImageOps.exif_transpose(orig)
            orig_w, orig_h = img.size
            title = get_exif_title(img)

            # 1. Display version (max 2560px for Retina / 4K)
            scale = min(1.0, DISPLAY_MAX_DIM / max(orig_w, orig_h))
            disp_w = int(orig_w * scale)
            disp_h = int(orig_h * scale)
            if scale < 1.0:
                disp_img = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            else:
                disp_img = img.copy()

            # Convert to RGB if needed (strip alpha for JPEG)
            if disp_img.mode in ("RGBA", "P"):
                disp_rgb = disp_img.convert("RGB")
            else:
                disp_rgb = disp_img

            disp_rgb.save(display_jpg, "JPEG", quality=JPG_QUALITY, optimize=True)
            disp_rgb.save(display_webp, "WEBP", quality=WEBP_QUALITY)

            # 2. Thumbnail version (fixed height 360px for mosaic)
            t_scale = THUMB_HEIGHT / orig_h
            t_w = int(orig_w * t_scale)
            t_h = THUMB_HEIGHT
            t_img = disp_img.resize((t_w, t_h), Image.Resampling.LANCZOS)
            if t_img.mode in ("RGBA", "P"):
                t_rgb = t_img.convert("RGB")
            else:
                t_rgb = t_img

            t_rgb.save(thumb_jpg, "JPEG", quality=JPG_QUALITY, optimize=True)
            t_rgb.save(thumb_webp, "WEBP", quality=WEBP_QUALITY)

        info = {
            "filename": src_path.name,
            "stem": stem,
            "orig_width": orig_w,
            "orig_height": orig_h,
            "disp_width": disp_w,
            "disp_height": disp_h,
            "thumb_width": t_w,
            "thumb_height": t_h,
            "exif_title": title,
            "aspect_ratio": round(orig_w / orig_h, 3)
        }
        self.cache[cache_key] = info
        return info

    def discover_galleries(self):
        if not GALLERIES_DIR.exists():
            return []

        folder_list = sorted([d for d in GALLERIES_DIR.iterdir() if d.is_dir()])
        galleries_data = []

        slug_map = {
            "01_people": ("people", "PEOPLE"),
            "02_nature": ("nature", "NATURE"),
            "03_rituals": ("rituals", "RITUALS & TRADITIONS"),
            "04_celebrations": ("traditions", "CELEBRATIONS"),
            "05_religion": ("religion", "RELIGION"),
            "06_cities": ("cities", "CITIES"),
            "07_bw": ("bw", "B/W"),
        }

        for folder in folder_list:
            raw_name = folder.name
            if raw_name in slug_map:
                slug, label = slug_map[raw_name]
            else:
                clean = re.sub(r'^\d+[\s_-]*', '', raw_name)
                slug = clean.lower().replace(" ", "-").replace("_", "-")
                label = clean.replace("-", " ").replace("_", " ").upper()

            extensions = {".jpg", ".jpeg", ".png", ".webp"}
            image_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in extensions]

            existing_meta_list = self.metadata.get(raw_name, [])
            meta_by_filename = {item.get("filename"): item for item in existing_meta_list if "filename" in item}

            def sort_key(f: Path):
                if f.name in meta_by_filename:
                    for idx, m in enumerate(existing_meta_list):
                        if m.get("filename") == f.name:
                            return (0, idx)
                return (1, f.name.lower())

            image_files.sort(key=sort_key)

            galleries_data.append({
                "folder": folder,
                "folder_name": raw_name,
                "slug": slug,
                "label": label,
                "image_files": image_files,
                "meta_by_filename": meta_by_filename
            })

        return galleries_data

    def discover_home_slides(self):
        if not HOME_SLIDES_DIR.exists():
            return []
        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in HOME_SLIDES_DIR.iterdir() if f.is_file() and f.suffix.lower() in extensions]
        files.sort(key=lambda x: x.name)
        return files

    def build(self):
        print("=== Starting Build for ferminezcurdia.com ===")
        DIST_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Copy static assets
        dist_assets = DIST_DIR / "assets"
        dist_assets.mkdir(parents=True, exist_ok=True)
        if STATIC_SRC_DIR.exists():
            shutil.copytree(STATIC_SRC_DIR, dist_assets, dirs_exist_ok=True)
            print("  [Static] Copied static assets to dist/assets/")

        # Copy favicon to root for browsers looking for /favicon.ico or /favicon.svg
        if (STATIC_SRC_DIR / "favicon.svg").exists():
            shutil.copy(STATIC_SRC_DIR / "favicon.svg", DIST_DIR / "favicon.svg")

        # 2. Write CNAME
        with open(DIST_DIR / "CNAME", "w", encoding="utf-8") as f:
            f.write("ferminezcurdia.com\n")

        # 3. Discover content
        galleries = self.discover_galleries()
        home_slide_files = self.discover_home_slides()
        print(f"  [Discovery] Found {len(galleries)} galleries and {len(home_slide_files)} home slides.")

        # 4. Process Home Slides
        dist_home_images = dist_assets / "images" / "home"
        dist_home_images.mkdir(parents=True, exist_ok=True)
        processed_slides = []
        for sf in home_slide_files:
            info = self.process_image(sf, dist_home_images)
            processed_slides.append({
                "filename": sf.name,
                "jpg_url": f"/assets/images/home/display/{info['stem']}.jpg",
                "webp_url": f"/assets/images/home/display/{info['stem']}.webp",
            })
        print(f"  [Home] Processed {len(processed_slides)} hero slides.")

        # 5. Process Galleries
        processed_galleries = []
        for g in galleries:
            g_dest_dir = dist_assets / "images" / "galleries" / g["slug"]
            g_dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"  [Gallery] Processing {g['label']} ({len(g['image_files'])} images)...")

            photos = []
            for img_path in g["image_files"]:
                info = self.process_image(img_path, g_dest_dir)
                meta = g["meta_by_filename"].get(img_path.name, {})
                title = meta.get("title") or info.get("exif_title") or format_title_from_filename(img_path.name)

                photos.append({
                    "filename": img_path.name,
                    "title": title,
                    "aspect_ratio": info["aspect_ratio"],
                    "width": info["disp_width"],
                    "height": info["disp_height"],
                    "thumb_width": info["thumb_width"],
                    "thumb_height": info["thumb_height"],
                    "thumb_webp": f"/assets/images/galleries/{g['slug']}/thumbs/{info['stem']}.webp",
                    "thumb_jpg": f"/assets/images/galleries/{g['slug']}/thumbs/{info['stem']}.jpg",
                    "full_webp": f"/assets/images/galleries/{g['slug']}/display/{info['stem']}.webp",
                    "full_jpg": f"/assets/images/galleries/{g['slug']}/display/{info['stem']}.jpg",
                })

            processed_galleries.append({
                "slug": g["slug"],
                "label": g["label"],
                "photos": photos
            })

        self.save_cache()

        # 6. Render HTML pages
        self.render_pages(processed_slides, processed_galleries)
        print("=== Build Complete! Site generated in dist/ ===")

    def get_sidebar_html(self, current_slug: str, galleries: list) -> str:
        menu_items = []

        home_active = ' class="active"' if current_slug == "home" else ''
        menu_items.append(f'<li{home_active}><a href="/">HOME</a></li>')

        for g in galleries:
            active = ' class="active"' if current_slug == g["slug"] else ''
            menu_items.append(f'<li{active}><a href="/{g["slug"]}/">{g["label"]}</a></li>')

        menu_items.append('<li><a href="https://www.flickr.com/photos/ezcurdia/albums" target="_blank" rel="noopener">FLICKR</a></li>')

        menu_html = "\n        ".join(menu_items)

        return f"""
        <header id="site-header">
            <div class="branding">
                <a href="/" class="site-title">
                    <h1>Fermín<br>Ezcurdia</h1>
                </a>
                <button id="menu-toggle" aria-label="Abrir menú" aria-expanded="false">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
            </div>
            <nav id="site-nav">
                <ul>
                    {menu_html}
                </ul>
            </nav>
        </header>
        """

    def render_pages(self, home_slides: list, galleries: list):
        # 1. Render Home (index.html)
        home_sidebar = self.get_sidebar_html("home", galleries)
        slides_json = json.dumps(home_slides)
        first_slide_jpg = home_slides[0]["jpg_url"] if home_slides else "/assets/images/home/display/1.jpg"

        home_json_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Fermín Ezcurdia",
            "url": "https://ferminezcurdia.com/",
            "jobTitle": "Fotógrafo",
            "description": "Portfolio y galerías de fotografía de Fermín Ezcurdia."
        }, ensure_ascii=False)

        home_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fermín Ezcurdia | Fotografía</title>
    <meta name="description" content="Portfolio y galerías de fotografía de Fermín Ezcurdia. Retratos, naturaleza, rituales, tradiciones, religiones y ciudades del mundo.">
    <link rel="canonical" href="https://ferminezcurdia.com/">
    <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
    <!-- Open Graph / Facebook / WhatsApp -->
    <meta property="og:site_name" content="Fermín Ezcurdia">
    <meta property="og:type" content="website">
    <meta property="og:title" content="Fermín Ezcurdia | Fotografía">
    <meta property="og:description" content="Portfolio y galerías de fotografía de Fermín Ezcurdia. Retratos, naturaleza, rituales y culturas del mundo.">
    <meta property="og:url" content="https://ferminezcurdia.com/">
    <meta property="og:image" content="https://ferminezcurdia.com{first_slide_jpg}">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Fermín Ezcurdia | Fotografía">
    <meta name="twitter:description" content="Portfolio y galerías de fotografía de Fermín Ezcurdia.">
    <meta name="twitter:image" content="https://ferminezcurdia.com{first_slide_jpg}">
    <link rel="stylesheet" href="/assets/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Droid+Serif:ital,wght@0,400;0,700;1,400&family=Oswald:wght@300;400;500&display=swap" rel="stylesheet">
    <script type="application/ld+json">
    {home_json_ld}
    </script>
</head>
<body class="page-home">
    <div id="layout-container">
        {home_sidebar}
        <main id="main-content" class="home-main">
            <div id="slideshow-container"></div>
        </main>
    </div>
    <script>
        const HOME_SLIDES = {slides_json};
    </script>
    <script src="/assets/js/slideshow.js"></script>
    <script src="/assets/js/main.js"></script>
</body>
</html>
"""
        with open(DIST_DIR / "index.html", "w", encoding="utf-8") as f:
            f.write(home_html)
        print("  [Render] Generated dist/index.html")

        # 2. Render Galleries
        num_galleries = len(galleries)
        for idx, g in enumerate(galleries):
            g_dir = DIST_DIR / g["slug"]
            g_dir.mkdir(parents=True, exist_ok=True)
            g_sidebar = self.get_sidebar_html(g["slug"], galleries)

            # Circular pagination
            prev_g = galleries[(idx - 1) % num_galleries]
            next_g = galleries[(idx + 1) % num_galleries]

            # Representative cover image for social sharing
            cover_photo = g["photos"][0]["full_jpg"] if g["photos"] else first_slide_jpg

            # Photos HTML for PhotoSwipe v5 Masonry Grid
            photos_html_list = []
            for p in g["photos"]:
                title_attr = p["title"].replace('"', '&quot;')
                item_html = f"""
                <div class="gallery-item" style="--aspect-ratio: {p['aspect_ratio']};">
                    <a href="{p['full_webp']}"
                       data-pswp-width="{p['width']}"
                       data-pswp-height="{p['height']}"
                       data-cropped="true"
                       target="_blank"
                       rel="noopener">
                        <picture>
                            <source srcset="{p['thumb_webp']}" type="image/webp">
                            <img src="{p['thumb_jpg']}"
                                 alt="{title_attr}"
                                 loading="lazy"
                                 width="{p['thumb_width']}"
                                 height="{p['thumb_height']}" />
                        </picture>
                        <div class="caption-overlay">
                            <span>{title_attr}</span>
                        </div>
                    </a>
                </div>"""
                photos_html_list.append(item_html)

            photos_block = "\n".join(photos_html_list)

            gallery_json_ld = json.dumps({
                "@context": "https://schema.org",
                "@type": "ImageGallery",
                "name": g["label"],
                "url": f"https://ferminezcurdia.com/{g['slug']}/",
                "creator": {
                    "@type": "Person",
                    "name": "Fermín Ezcurdia",
                    "url": "https://ferminezcurdia.com/"
                }
            }, ensure_ascii=False)

            gallery_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{g['label']} | Fermín Ezcurdia</title>
    <meta name="description" content="Galería fotográfica {g['label']} de Fermín Ezcurdia. Fotografías originales en alta definición.">
    <link rel="canonical" href="https://ferminezcurdia.com/{g['slug']}/">
    <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
    <!-- Open Graph / Facebook / WhatsApp -->
    <meta property="og:site_name" content="Fermín Ezcurdia">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{g['label']} | Fermín Ezcurdia">
    <meta property="og:description" content="Galería de fotografía {g['label']} por Fermín Ezcurdia.">
    <meta property="og:url" content="https://ferminezcurdia.com/{g['slug']}/">
    <meta property="og:image" content="https://ferminezcurdia.com{cover_photo}">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{g['label']} | Fermín Ezcurdia">
    <meta name="twitter:description" content="Galería fotográfica {g['label']} de Fermín Ezcurdia.">
    <meta name="twitter:image" content="https://ferminezcurdia.com{cover_photo}">
    <link rel="stylesheet" href="/assets/css/style.css">
    <link rel="stylesheet" href="/assets/vendor/photoswipe/photoswipe.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Droid+Serif:ital,wght@0,400;0,700;1,400&family=Oswald:wght@300;400;500&display=swap" rel="stylesheet">
    <script type="application/ld+json">
    {gallery_json_ld}
    </script>
</head>
<body class="page-gallery">
    <div id="layout-container">
        {g_sidebar}
        <main id="main-content" class="gallery-main">
            <h1 class="gallery-title">{g['label']}</h1>
            <div id="photo-gallery" class="pswp-gallery masonry-grid">
                {photos_block}
            </div>
            <!-- End of gallery navigation -->
            <nav class="gallery-pagination">
                <a href="/{prev_g['slug']}/" class="pagination-link prev">
                    <span class="pagination-sub">Galería anterior</span>
                    <span class="pagination-title">← {prev_g['label']}</span>
                </a>
                <a href="/{next_g['slug']}/" class="pagination-link next">
                    <span class="pagination-sub">Siguiente galería</span>
                    <span class="pagination-title">{next_g['label']} →</span>
                </a>
            </nav>
        </main>
    </div>
    <!-- Floating Back to Top Button -->
    <button id="back-to-top" aria-label="Volver arriba" title="Volver arriba">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </button>
    <script type="module">
        import PhotoSwipeLightbox from '/assets/vendor/photoswipe/photoswipe-lightbox.esm.min.js';
        const lightbox = new PhotoSwipeLightbox({{
            gallery: '#photo-gallery',
            children: 'a',
            pswpModule: () => import('/assets/vendor/photoswipe/photoswipe.esm.min.js'),
            padding: {{ top: 20, bottom: 40, left: 20, right: 20 }},
            bgOpacity: 0.94,
            wheelToZoom: true
        }});

        // Custom caption plugin for PhotoSwipe v5
        lightbox.on('uiRegister', function() {{
            lightbox.pswp.ui.registerElement({{
                name: 'custom-caption',
                order: 9,
                isButton: false,
                appendTo: 'root',
                html: '',
                onInit: (el, pswp) => {{
                    el.style.display = 'none';
                    lightbox.pswp.on('change', () => {{
                        const currSlide = lightbox.pswp.currSlide;
                        let captionText = '';
                        if (currSlide && currSlide.data && currSlide.data.element) {{
                            const img = currSlide.data.element.querySelector('img');
                            if (img) captionText = img.getAttribute('alt') || '';
                        }}
                        if (captionText) {{
                            el.textContent = captionText;
                            el.style.display = 'block';
                        }} else {{
                            el.textContent = '';
                            el.style.display = 'none';
                        }}
                    }});
                }}
            }});
        }});

        // High-res Image Protection in Lightbox: disable right-click contextmenu on high-res photos
        lightbox.on('afterInit', () => {{
            lightbox.pswp.element.addEventListener('contextmenu', (e) => {{
                if (e.target.tagName === 'IMG' || e.target.closest('.pswp__img')) {{
                    e.preventDefault();
                }}
            }});
        }});

        lightbox.init();
    </script>
    <script src="/assets/js/main.js"></script>
</body>
</html>
"""
            with open(g_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(gallery_html)
            print(f"  [Render] Generated dist/{g['slug']}/index.html")

if __name__ == "__main__":
    builder = SiteBuilder()
    builder.build()
