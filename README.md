# Portfolio Fotográfico - Fermín Ezcurdia

Sitio web estático moderno y de alto rendimiento para el portfolio de fotografía de [ferminezcurdia.com](https://ferminezcurdia.com/), migrado desde WordPress a **GitHub Pages** con aceleración CDN y caché global en **Cloudflare**.

---

## 📸 Cómo Gestionar las Fotos (Flujo "Folder-Drop")

El fotógrafo no necesita tocar código: todo se gestiona con carpetas dentro de `content/` y el botón de publicar. La guía para Fermín está en [GUIA_PUBLICAR_FOTOS.md](GUIA_PUBLICAR_FOTOS.md).

* **Galerías:** una carpeta por galería en `content/galleries/` (`08_japon/`). El número fija la posición en el menú y el resto da la URL (`/japon/`, sin acentos) y el título del menú. Las 7 galerías originales conservan sus URLs aunque se renumeren (`GALLERY_OVERRIDES` en `build.py`). Una carpeta sin fotos no aparece en el menú.
* **Portada:** `content/home_slides/`, en orden de nombre.
* **Orden de fotos:** primero las numeradas por el fotógrafo (`01_`, `02_`...), luego las heredadas del WordPress en su orden original (`existing_site_metadata.json`) y luego el resto por nombre.
* **Títulos:** título del WordPress antiguo → título de Lightroom (XMP `dc:title` / IPTC) → EXIF `ImageDescription` (ignorando textos de cámara como "OLYMPUS DIGITAL CAMERA") → nombre del archivo limpio.
* **Formatos:** JPG, PNG, WebP, TIFF y HEIC. `content/.gitignore` solo deja entrar en git esos formatos, así que vídeos, documentos o RAW nunca se suben.

### Botón de publicar (`PUBLICAR_WEB.bat` / `PUBLICAR_WEB.command`)

Lanzan `scripts/publicar.ps1` (Windows) o `scripts/publicar.sh` (Mac), que hacen lo mismo:

1. Reducen a 3000 px de lado largo las fotos nuevas o cambiadas que lo superen (System.Drawing en Windows, `sips` en Mac, conservando EXIF y perfil de color), convierten TIFF/BMP a JPG, avisan de los archivos que no son fotos y dejan fuera los de más de 45 MB. Así los originales de cámara no engordan para siempre el historial de git.
2. Configuran `user.name`/`user.email` si faltan, hacen commit solo de `content/` y comprueban cada paso.
3. Traen los cambios del repositorio (`fetch` + `rebase --autostash`); si hay conflicto lo deshacen y piden avisar a Iñigo sin perder nada.
4. Hacen `push` y distinguen falta de internet, problemas de acceso y otros errores, siempre en castellano llano.
5. Esperan a que `https://ferminezcurdia.com/estado-publicacion.json` muestre ese commit (o uno posterior) y enseñan los avisos de la compilación (fotos dañadas, etc.).

`INSTALAR_ACCESOS_DIRECTOS.bat` / `.command` crean los iconos del Escritorio (galerías, portada y publicar), configuran la identidad de git y prueban el acceso a GitHub con `git push --dry-run`.

---

## 🛠️ Arquitectura Técnica

* **Motor estático:** Generador en Python (`site_generator/build.py`) con Pillow y pillow-heif.
* **Procesado incremental:** `.cache/` guarda las dimensiones por hash SHA-256 del archivo; solo se procesan las fotos nuevas o cambiadas. Subir `PROCESSING_VERSION` fuerza el reprocesado de todo.
* **Imágenes generadas:** todas convertidas a sRGB (las fotos en Adobe RGB, ProPhoto o CMYK se ven con sus colores reales).
  * **Miniaturas:** 360 px de alto en WebP, con JPG de respaldo.
  * **Visualización:** máximo 2560 px en WebP. Solo la primera foto de cada galería y de la portada tiene además JPG, para compartir en redes (Open Graph).
* **Limpieza:** las imágenes y páginas de fotos o galerías que ya no existen se borran de `dist/`, así que una foto retirada deja de estar accesible por su URL.
* **Robustez:** una foto dañada no detiene la compilación; se omite y se anota en `dist/estado-publicacion.json` (`commit`, `fecha`, `avisos`), que el botón de publicar muestra al fotógrafo.
* **Frontend:**
  * Mosaico justificado con aspect-ratio precalculado (CLS = 0) y `loading="lazy"`.
  * **PhotoSwipe v5** empaquetado localmente: zoom, gestos táctiles, teclado y títulos.
  * La portada solo descarga cada diapositiva justo antes de mostrarla.
* **Despliegue:** GitHub Actions (`.github/workflows/deploy.yml`) compila y publica en la rama `gh-pages`.

---

## 💻 Desarrollo y Compilación Local

Para compilar o probar la web en tu equipo:

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Compilar el sitio:**
   ```bash
   python site_generator/build.py
   ```
   *(La web estática se generará en el directorio `dist/`).*

3. **Previsualizar localmente:**
   ```bash
   python -m http.server 8000 --directory dist
   ```
   Abre [http://localhost:8000](http://localhost:8000) en tu navegador.
