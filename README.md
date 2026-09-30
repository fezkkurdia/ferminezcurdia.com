# Portfolio Fotográfico - Fermín Ezcurdia

Sitio web estático moderno y de alto rendimiento para el portfolio de fotografía de [ferminezcurdia.com](https://ferminezcurdia.com/), migrado desde WordPress a **GitHub Pages** con aceleración CDN y caché global en **Cloudflare**.

---

## 📸 Cómo Gestionar las Fotos (Flujo "Folder-Drop")

El fotógrafo no necesita tocar código ni bases de datos. Todo el contenido se gestiona directamente mediante carpetas y archivos en el directorio `content/`:

### 1. Añadir una nueva Galería
1. Crea una carpeta dentro de `content/galleries/` con un número opcional de orden y el nombre de la galería:
   * Ejemplo: `content/galleries/08_japon/` o `content/galleries/08_tokyo/`
2. Vuelca las fotografías originales en su interior (`.jpg`, `.jpeg`, `.png`, `.webp`).
3. Haz commit y push a GitHub:
   ```bash
   git add .
   git commit -m "Añadida galería de Japón"
   git push
   ```
   *(También se puede arrastrar la carpeta directamente desde la web de GitHub o GitHub Desktop).*
4. GitHub Actions detectará la nueva carpeta, optimizará las imágenes, generará los thumbnails, actualizará el menú de navegación y publicará la web automáticamente en ~1-2 minutos.

### 2. Títulos y Orden de las Fotos
* **Títulos automáticos:** El sistema limpia el nombre del archivo (ejemplo: `01_Pescador_en_el_rio.jpg` se mostrará como *"Pescador en el rio"*). Si la cámara tiene títulos guardados en los metadatos EXIF, el sistema los leerá automáticamente.
* **Orden:** Las fotos se ordenan por su nombre de archivo. Puedes numerarlas al inicio (`01_foto.jpg`, `02_foto.jpg`) para fijar un orden concreto.

### 3. Fotos de la Portada (Slideshow Home)
* Las 10 fotos heroicas que rotan a pantalla completa en la página de inicio se encuentran en:
  `content/home_slides/`
* Para cambiar una foto de portada, basta con añadir o sustituir imágenes en esa carpeta.

---

## 🛠️ Arquitectura Técnica

* **Motor estático:** Generador en Python (`site_generator/build.py`) con Pillow.
* **Procesado incremental inteligente:** Utiliza `.cache/` y hashes SHA-256 para no volver a procesar imágenes ya existentes. Las compilaciones posteriores tardan menos de 1 segundo.
* **Formatos de imagen generados:**
  * **Miniaturas (Thumbs):** Altura 360px en WebP (~15-30 KB) y JPG de respaldo.
  * **Visualización (Display):** Máximo 2560px (Retina/4K) en WebP (~200-400 KB) con máxima fidelidad fotográfica y JPG de respaldo.
* **Frontend:**
  * Maquetación limpia basada en flexbox con aspect-ratio para cuadrícula en mosaico justificado.
  * Cero saltos visuales de maquetación (CLS = 0) gracias al precálculo de dimensiones.
  * **PhotoSwipe v5** empaquetado localmente: zoom con rueda de ratón, gestos táctiles en móviles, teclado y títulos elegantes.
  * Carga diferida nativa (`loading="lazy"`).
* **Despliegue:** GitHub Actions (`.github/workflows/deploy.yml`) hacia GitHub Pages.

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
