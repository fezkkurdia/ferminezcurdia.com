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
import html
import io
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps, ImageCms, IptcImagePlugin

# HEIC/HEIF (iPhone) support, optional so local builds work without it
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

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
STATUS_FILENAME = "estado-publicacion.json"

# Settings
THUMB_HEIGHT = 360
DISPLAY_MAX_DIM = 2560  # Ultra-crisp 4K/Retina display resolution
JPG_QUALITY = 84
WEBP_QUALITY = 82
# Bump when image processing changes so cached outputs are regenerated
PROCESSING_VERSION = 2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
if HEIF_SUPPORTED:
    IMAGE_EXTENSIONS |= {".heic", ".heif"}

# Numbering prefix the photographer uses to force an order (01_, 2-, 003 ...).
# Limited to 4 digits so Flickr-style ids (51197730626_...) don't count.
ORDER_PREFIX_RE = re.compile(r'^(\d{1,4})[\s_-]+')

# Fixed URLs and menu labels of the original galleries, keyed by folder name
# without its number so renumbering a folder keeps its URL.
GALLERY_OVERRIDES = {
    "people": ("people", "PEOPLE"),
    "nature": ("nature", "NATURE"),
    "rituals": ("rituals", "RITUALS & TRADITIONS"),
    "celebrations": ("traditions", "CELEBRATIONS"),
    "religion": ("religion", "RELIGION"),
    "cities": ("cities", "CITIES"),
    "bw": ("bw", "B/W"),
}

# Text some cameras write into ImageDescription that is not a real title
JUNK_DESCRIPTIONS = re.compile(
    r'^(|.*digital camera.*|sony dsc|default|untitled|image|picture|photo|'
    r'samsung|lg digital camera|kodak.*|minolta.*|sanyo.*|cimg\d*|dsc\w*|img_?\d*)$',
    re.IGNORECASE)

SRGB_PROFILE = ImageCms.createProfile("sRGB")

def friendly_path(path: Path) -> str:
    """How the photographer sees a content path: «08_japon/foto.jpg» or «portada/foto.jpg»."""
    rel = path.relative_to(CONTENT_DIR).as_posix()
    if rel.startswith("galleries/"):
        return rel[len("galleries/"):]
    if rel.startswith("home_slides/"):
        return "portada/" + rel[len("home_slides/"):]
    return rel

def strip_number_prefix(name: str) -> str:
    return ORDER_PREFIX_RE.sub('', name)

def natural_key(text: str):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', text.lower())]

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return text or "galeria"

# Clean Title Formatter
def format_title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    # Remove leading numbering like 01_, 001-, etc.
    stem = re.sub(r'^\d+[\s_-]*', '', stem)
    # Replace dashes and underscores
    clean = re.sub(r'[\s_-]+', ' ', stem).strip()
    return clean

def _decode(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else b""
    if isinstance(value, bytes):
        for enc in ("utf-8", "latin-1"):
            try:
                return value.decode(enc).strip()
            except UnicodeDecodeError:
                continue
    return str(value).strip() if value else ""

# Title written by Lightroom/Photoshop (XMP dc:title, IPTC Title) or the camera (EXIF)
def get_embedded_title(img: Image.Image) -> str:
    try:
        xmp = img.info.get("xmp") or img.info.get("XML:com.adobe.xmp")
        if xmp:
            if isinstance(xmp, bytes):
                xmp = xmp.decode("utf-8", "ignore")
            m = re.search(r'<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>', xmp, re.DOTALL)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
    except Exception:
        pass
    try:
        iptc = IptcImagePlugin.getiptcinfo(img) or {}
        title = _decode(iptc.get((2, 5)))  # IPTC Object Name = Lightroom "Title"
        if title:
            return title
    except Exception:
        pass
    try:
        desc = img.getexif().get(0x010e)  # EXIF ImageDescription
        desc = _decode(desc)
        if desc and not JUNK_DESCRIPTIONS.match(desc):
            return desc
    except Exception:
        pass
    return ""

def to_srgb(img: Image.Image) -> Image.Image:
    """Converts any colour space (Adobe RGB, ProPhoto, CMYK...) to sRGB for the web."""
    icc = img.info.get("icc_profile")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if "srgb" in ImageCms.getProfileDescription(src).lower() and img.mode in ("RGB", "RGBA"):
                return img  # already web colours
            out_mode = "RGBA" if img.mode in ("RGBA", "LA", "PA") else "RGB"
            if img.mode not in ("RGB", "RGBA", "CMYK", "L"):
                img = img.convert("RGBA" if out_mode == "RGBA" else "RGB")
            return ImageCms.profileToProfile(img, src, SRGB_PROFILE, outputMode=out_mode)
        except Exception:
            pass
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        return img.convert("RGBA")
    return img.convert("RGB") if img.mode != "RGB" else img

def flatten(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (22, 22, 22))  # site background (#161616)
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert("RGB") if img.mode != "RGB" else img

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
        self.expected_files = set()
        self.warnings = []

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

    def process_image(self, src_path: Path, dest_gallery_dir: Path, out_stem: str, display_jpg_needed: bool = False):
        """Generates thumb (WebP + JPG fallback) and display (WebP, plus JPG when used
        as a social sharing image) versions, converted to sRGB."""
        file_hash = compute_file_hash(src_path)
        out_dir = dest_gallery_dir.relative_to(DIST_DIR).as_posix()
        cache_key = f"{out_dir}/{out_stem}_{file_hash}_{DISPLAY_MAX_DIM}_v{PROCESSING_VERSION}"

        thumb_dir = dest_gallery_dir / "thumbs"
        display_dir = dest_gallery_dir / "display"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        display_dir.mkdir(parents=True, exist_ok=True)

        thumb_jpg = thumb_dir / f"{out_stem}.jpg"
        thumb_webp = thumb_dir / f"{out_stem}.webp"
        display_jpg = display_dir / f"{out_stem}.jpg"
        display_webp = display_dir / f"{out_stem}.webp"

        outputs = [thumb_jpg, thumb_webp, display_webp]
        if display_jpg_needed:
            outputs.append(display_jpg)
        self.expected_files.update(outputs)

        # Check if already cached and exists
        if cache_key in self.cache and all(o.exists() for o in outputs):
            return self.cache[cache_key]

        # Process image
        with Image.open(src_path) as orig:
            orig.load()
            title = get_embedded_title(orig)
            # Auto-orient based on EXIF, then normalise colours to sRGB
            img = to_srgb(ImageOps.exif_transpose(orig))
            orig_w, orig_h = img.size

            # 1. Display version (max 2560px for Retina / 4K)
            scale = min(1.0, DISPLAY_MAX_DIM / max(orig_w, orig_h))
            disp_w = max(1, int(orig_w * scale))
            disp_h = max(1, int(orig_h * scale))
            if scale < 1.0:
                disp_img = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            else:
                disp_img = img.copy()

            disp_rgb = flatten(disp_img)
            disp_rgb.save(display_webp, "WEBP", quality=WEBP_QUALITY)
            if display_jpg_needed:
                disp_rgb.save(display_jpg, "JPEG", quality=JPG_QUALITY, optimize=True)

            # 2. Thumbnail version (fixed height 360px for mosaic)
            t_scale = THUMB_HEIGHT / disp_h
            t_w = max(1, int(disp_w * t_scale))
            t_h = THUMB_HEIGHT
            t_rgb = disp_rgb.resize((t_w, t_h), Image.Resampling.LANCZOS)
            t_rgb.save(thumb_jpg, "JPEG", quality=JPG_QUALITY, optimize=True)
            t_rgb.save(thumb_webp, "WEBP", quality=WEBP_QUALITY)

        info = {
            "filename": src_path.name,
            "stem": out_stem,
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

    def safe_process(self, src_path: Path, dest_dir: Path, out_stem: str, display_jpg_needed: bool = False):
        """Like process_image, but a broken photo is skipped with a warning instead of
        stopping the whole build (and leaving the website un-updated)."""
        try:
            return self.process_image(src_path, dest_dir, out_stem, display_jpg_needed)
        except Exception as e:
            rel = friendly_path(src_path)
            print(f"  [AVISO] No se ha podido procesar {rel}: {e}")
            self.warnings.append(f"La foto «{rel}» no se ha podido publicar (el archivo parece dañado o no es una imagen válida).")
            return None

    def list_images(self, folder: Path) -> list:
        """Image files of a folder; anything else is reported (except system files)."""
        images = []
        for f in folder.iterdir():
            if f.name.startswith(".") or f.name.lower() in ("thumbs.db", "desktop.ini"):
                continue
            if f.is_dir():
                self.warnings.append(f"La carpeta «{friendly_path(f)}» está dentro de una galería: sus fotos no se muestran. "
                                     "Saca las fotos de esa carpeta o conviértela en una galería propia.")
            elif f.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(f)
            else:
                self.warnings.append(f"«{friendly_path(f)}» no es un tipo de foto que la web pueda mostrar (usa JPG).")
        return images

    @staticmethod
    def unique_stems(files: list) -> dict:
        """Output name per file; foto.jpg and foto.png in one folder must not overwrite each other."""
        counts = {}
        for f in files:
            counts[f.stem.lower()] = counts.get(f.stem.lower(), 0) + 1
        return {f: (f.stem if counts[f.stem.lower()] == 1 else f"{f.stem}-{f.suffix.lstrip('.').lower()}")
                for f in files}

    def discover_galleries(self):
        if not GALLERIES_DIR.exists():
            return []

        folder_list = sorted([d for d in GALLERIES_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")],
                             key=lambda d: natural_key(d.name))
        galleries_data = []
        used_slugs = set()

        # Legacy WordPress metadata, findable even if the folder gets renumbered
        legacy_by_name = {strip_number_prefix(k): v for k, v in self.metadata.items()}

        for folder in folder_list:
            raw_name = folder.name
            clean = strip_number_prefix(raw_name).strip() or raw_name
            override = GALLERY_OVERRIDES.get(clean.lower())
            if override:
                slug, label = override
            else:
                slug = slugify(clean)
                label = re.sub(r'[_-]+', ' ', clean).strip().upper()
            base_slug, n = slug, 2
            while slug in used_slugs or slug == "assets":
                slug, n = f"{base_slug}-{n}", n + 1
            used_slugs.add(slug)

            image_files = self.list_images(folder)

            existing_meta_list = self.metadata.get(raw_name) or legacy_by_name.get(clean, [])
            meta_by_filename = {item.get("filename"): item for item in existing_meta_list if "filename" in item}
            legacy_order = {item.get("filename"): idx for idx, item in enumerate(existing_meta_list)}

            # 1) photos the photographer numbered (01_, 02_...), in that order
            # 2) photos from the old website, in their original order
            # 3) everything else, by name
            def sort_key(f: Path):
                if f.name not in legacy_order and ORDER_PREFIX_RE.match(f.name):
                    return (0, 0, natural_key(f.name))
                if f.name in legacy_order:
                    return (1, legacy_order[f.name], [])
                return (2, 0, natural_key(f.name))

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
        files = self.list_images(HOME_SLIDES_DIR)
        files.sort(key=lambda x: natural_key(x.name))
        return files

    def legacy_title(self, filename: str, meta_by_filename: dict) -> str:
        meta = meta_by_filename.get(filename) or meta_by_filename.get(strip_number_prefix(filename)) or {}
        return meta.get("title") or ""

    def remove_stale_outputs(self, gallery_slugs: list):
        """Deletes processed images and pages of photos/galleries that no longer exist,
        so a removed photo is really gone from the website."""
        removed = 0
        images_root = DIST_DIR / "assets" / "images"
        for sub in ("home", "galleries"):
            root = images_root / sub
            if not root.exists():
                continue
            for f in root.rglob("*"):
                if f.is_file() and f not in self.expected_files:
                    f.unlink()
                    removed += 1
            for d in sorted((d for d in root.rglob("*") if d.is_dir()), key=lambda d: len(d.parts), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
        for d in DIST_DIR.iterdir():
            if d.is_dir() and d.name != "assets" and d.name not in gallery_slugs and (d / "index.html").exists():
                shutil.rmtree(d)
                removed += 1
        if removed:
            print(f"  [Cleanup] Removed {removed} stale files/pages.")

    def write_status(self):
        """Small public file the publish button reads to confirm the new version is live."""
        commit = os.environ.get("GITHUB_SHA", "")
        if not commit:
            try:
                commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True,
                                        text=True, check=True).stdout.strip()
            except Exception:
                commit = ""
        status = {
            "commit": commit,
            "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "avisos": self.warnings,
        }
        with open(DIST_DIR / STATUS_FILENAME, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)

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

        # 2. Write CNAME and .nojekyll for GitHub Pages
        with open(DIST_DIR / "CNAME", "w", encoding="utf-8") as f:
            f.write("ferminezcurdia.com\n")
        (DIST_DIR / ".nojekyll").touch()

        # 3. Discover content
        galleries = self.discover_galleries()
        home_slide_files = self.discover_home_slides()
        print(f"  [Discovery] Found {len(galleries)} galleries and {len(home_slide_files)} home slides.")

        # 4. Process Home Slides
        dist_home_images = dist_assets / "images" / "home"
        dist_home_images.mkdir(parents=True, exist_ok=True)
        processed_slides = []
        home_stems = self.unique_stems(home_slide_files)
        for sf in home_slide_files:
            # The first slide doubles as the social sharing image, which needs a JPG
            info = self.safe_process(sf, dist_home_images, home_stems[sf], display_jpg_needed=not processed_slides)
            if not info:
                continue
            processed_slides.append({
                "filename": sf.name,
                "webp_url": f"/assets/images/home/display/{info['stem']}.webp",
                "jpg_url": f"/assets/images/home/display/{info['stem']}.jpg",
            })
        print(f"  [Home] Processed {len(processed_slides)} hero slides.")

        # 5. Process Galleries
        processed_galleries = []
        for g in galleries:
            g_dest_dir = dist_assets / "images" / "galleries" / g["slug"]
            g_dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"  [Gallery] Processing {g['label']} ({len(g['image_files'])} images)...")

            photos = []
            stems = self.unique_stems(g["image_files"])
            for img_path in g["image_files"]:
                # The first photo is the gallery's social sharing image (needs a JPG)
                info = self.safe_process(img_path, g_dest_dir, stems[img_path], display_jpg_needed=not photos)
                if not info:
                    continue
                title = (self.legacy_title(img_path.name, g["meta_by_filename"])
                         or info.get("exif_title") or format_title_from_filename(img_path.name))

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

            if not photos:
                print(f"  [Gallery] {g['label']} has no photos, left out of the menu.")
                continue

            processed_galleries.append({
                "slug": g["slug"],
                "label": g["label"],
                "photos": photos
            })

        # Forget cache entries of photos that no longer exist
        used = {str(p) for p in self.expected_files}
        self.cache = {k: v for k, v in self.cache.items()
                      if str(DIST_DIR / k.rsplit("/", 1)[0] / "thumbs" / f"{v['stem']}.webp") in used}
        self.save_cache()

        # 6. Render HTML pages
        self.render_pages(processed_slides, processed_galleries)
        self.remove_stale_outputs([g["slug"] for g in processed_galleries])
        self.write_status()
        if self.warnings:
            print("  [Avisos]")
            for w in self.warnings:
                print(f"    - {w}")
        print("=== Build Complete! Site generated in dist/ ===")

    def get_social_links_html(self, container_class: str = "social-nav") -> str:
        return f"""
            <div class="{container_class}" aria-label="Redes sociales">
                <a href="https://www.flickr.com/photos/ezcurdia/albums/" target="_blank" rel="noopener" class="social-link flickr" title="Flickr" aria-label="Flickr">
                    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                        <circle cx="7" cy="12" r="4.5" fill="#0063dc"/>
                        <circle cx="17" cy="12" r="4.5" fill="#ff0084"/>
                    </svg>
                </a>
                <a href="https://www.instagram.com/ferminezkurdia/?hl=es" target="_blank" rel="noopener" class="social-link instagram" title="Instagram" aria-label="Instagram">
                    <div class="instagram-icon-box">
                        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
                            <rect x="2" y="2" width="20" height="20" rx="5" fill="none" stroke="#ffffff" stroke-width="2.2"/>
                            <circle cx="12" cy="12" r="4.2" fill="none" stroke="#ffffff" stroke-width="2.2"/>
                            <circle cx="17" cy="7" r="1.2" fill="#ffffff"/>
                        </svg>
                    </div>
                </a>
                <a href="https://www.facebook.com/fermin.ezcurdia" target="_blank" rel="noopener" class="social-link facebook" title="Facebook" aria-label="Facebook">
                    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                        <circle cx="12" cy="12" r="11" fill="#1877F2"/>
                        <path d="M14.8 12.2h-2.1v6.8h-2.8v-6.8H8.5V9.8h1.4V8.1c0-1.9 1.1-3.1 3-3.1.9 0 1.9.1 1.9.1v2.1h-1.1c-1 0-1.2.6-1.2 1.2v1.4h2.5l-.2 2.4z" fill="#ffffff"/>
                    </svg>
                </a>
                <a href="https://lumenira.com/user/Fermin" target="_blank" rel="noopener" class="social-link lumenira" title="Lumenira" aria-label="Lumenira">
                    <picture>
                        <source srcset="/assets/images/lumenira.webp" type="image/webp">
                        <img src="/assets/images/lumenira.png" alt="Lumenira" width="26" height="11" class="lumenira-icon-img">
                    </picture>
                </a>
            </div>"""

    def get_sidebar_html(self, current_slug: str, galleries: list) -> str:
        menu_items = []

        home_active = ' class="active"' if current_slug == "home" else ''
        menu_items.append(f'<li{home_active}><a href="/">HOME</a></li>')

        for g in galleries:
            active = ' class="active"' if current_slug == g["slug"] else ''
            menu_items.append(f'<li{active}><a href="/{g["slug"]}/">{g["label"]}</a></li>')

        menu_html = "\n                    ".join(menu_items)
        social_html = self.get_social_links_html("menu-social-nav")

        return f"""
        <header id="site-header">
            <div class="branding">
                <a href="/" class="site-title" aria-label="Fermín Ezkurdia">
                    <h1 class="logo-heading">
                        <span class="sr-only">Fermín Ezkurdia</span>
                        <picture>
                            <source srcset="/assets/images/logo.webp" type="image/webp">
                            <img src="/assets/images/logo.png" alt="Fermín Ezkurdia" class="site-logo" width="180" height="54">
                        </picture>
                    </h1>
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
                {social_html}
            </nav>
        </header>
        """

    def get_home_mobile_footer_html(self) -> str:
        social_html = self.get_social_links_html("home-social-nav")
        return f"""
        <footer id="home-mobile-footer" aria-label="Redes sociales">
            {social_html}
        </footer>
        """

    def render_pages(self, home_slides: list, galleries: list):
        # Asset cache busting hashes
        css_file = STATIC_SRC_DIR / "css" / "style.css"
        css_v = compute_file_hash(css_file)[:8] if css_file.exists() else "1"
        js_file = STATIC_SRC_DIR / "js" / "main.js"
        js_v = compute_file_hash(js_file)[:8] if js_file.exists() else "1"
        slideshow_file = STATIC_SRC_DIR / "js" / "slideshow.js"
        slideshow_v = compute_file_hash(slideshow_file)[:8] if slideshow_file.exists() else "1"

        # 1. Render Home (index.html)
        home_sidebar = self.get_sidebar_html("home", galleries)
        home_mobile_footer = self.get_home_mobile_footer_html()
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, interactive-widget=resizes-content">
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
    <link rel="stylesheet" href="/assets/css/style.css?v={css_v}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Droid+Serif:ital,wght@0,400;0,700;1,400&family=Oswald:wght@300;400;500&display=swap" rel="stylesheet">
    <script>
        (function() {{
            function updateAppHeight() {{
                var h = window.visualViewport ? window.visualViewport.height : window.innerHeight;
                document.documentElement.style.setProperty('--app-height', Math.round(h) + 'px');
            }}
            function detectBottomBar() {{
                var isBrave = false;
                if (window.navigator) {{
                    if (window.navigator.brave) {{
                        isBrave = true;
                    }} else if (window.navigator.userAgentData && window.navigator.userAgentData.brands) {{
                        isBrave = window.navigator.userAgentData.brands.some(function(b) {{
                            return b.brand && b.brand.toLowerCase().indexOf('brave') !== -1;
                        }});
                    }}
                }}
                if (isBrave) {{
                    document.documentElement.classList.add('has-bottom-bar');
                    document.documentElement.style.setProperty('--bottom-bar-offset', '58px');
                }}
            }}
            updateAppHeight();
            detectBottomBar();
            if (window.navigator && window.navigator.brave && typeof window.navigator.brave.isBrave === 'function') {{
                window.navigator.brave.isBrave().then(function(b) {{
                    if (b) {{
                        document.documentElement.classList.add('has-bottom-bar');
                        document.documentElement.style.setProperty('--bottom-bar-offset', '58px');
                    }}
                }});
            }}
            window.addEventListener('resize', updateAppHeight);
            window.addEventListener('orientationchange', updateAppHeight);
            if (window.visualViewport) {{
                window.visualViewport.addEventListener('resize', updateAppHeight);
            }}
            document.addEventListener('DOMContentLoaded', function() {{
                updateAppHeight();
                detectBottomBar();
            }});
        }})();
    </script>
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
        {home_mobile_footer}
    </div>
    <script>
        const HOME_SLIDES = {slides_json};
    </script>
    <script src="/assets/js/slideshow.js?v={slideshow_v}"></script>
    <script src="/assets/js/main.js?v={js_v}"></script>
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
            for p_idx, p in enumerate(g["photos"]):
                title_attr = p["title"].replace('"', '&quot;')
                loading_attr = 'loading="eager" fetchpriority="high"' if p_idx < 8 else 'loading="lazy"'
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
                                 {loading_attr}
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
    <link rel="stylesheet" href="/assets/css/style.css?v={css_v}">
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
            wheelToZoom: true,
            preload: [1, 2]
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
    <script src="/assets/js/main.js?v={js_v}"></script>
</body>
</html>
"""
            with open(g_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(gallery_html)
            print(f"  [Render] Generated dist/{g['slug']}/index.html")

if __name__ == "__main__":
    builder = SiteBuilder()
    builder.build()
