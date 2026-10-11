# 📸 Guía para Actualizar la Web - Fermín Ezcurdia

Esta guía explica cómo se actualiza [ferminezcurdia.com](https://ferminezcurdia.com). No requiere conocimientos informáticos: todo se hace con carpetas normales del ordenador y un icono en el Escritorio.

---

## ⚙️ Configuración inicial (solo la primera vez, la hace Iñigo)

1. **Instalar Git:** descárgalo de [git-scm.com](https://git-scm.com/) e instálalo con las opciones por defecto (en Mac basta con abrir el Terminal y escribir `xcode-select --install`).
2. **Descargar la web** en una carpeta fija (por ejemplo `C:\ferminezcurdia.com` o `Documentos`):
   ```bash
   git clone https://github.com/fezkkurdia/ferminezcurdia.com.git
   ```
3. **Instalar los accesos directos:** doble clic en
   👉 `INSTALAR_ACCESOS_DIRECTOS.bat` (Windows) o `INSTALAR_ACCESOS_DIRECTOS.command` (Mac).

   El instalador:
   * Crea 3 iconos en el Escritorio: **`📸 FOTOS DE MI WEB`**, **`🖼️ FOTOS DE LA PORTADA`** y **`🚀 ACTUALIZAR MI WEB`**.
   * Configura el nombre con el que se guardan los cambios ("Fermín Ezcurdia").
   * **Comprueba el acceso a GitHub.** La primera vez se abre una ventana para iniciar sesión en GitHub: entra con una cuenta que tenga permiso de escritura en el repositorio (la de Fermín añadida como colaborador, o la de Iñigo). Windows (o el Llavero del Mac) guarda la sesión y Fermín no vuelve a verla.

> **Si el ordenador de Fermín ya estaba configurado con la versión anterior**, abre una vez una terminal en la carpeta de la web y ejecuta `git pull`, y luego vuelve a lanzar el instalador para que aparezca el icono de la portada. El botón antiguo no sabía descargar los cambios de Iñigo y fallaría.

---

## 📝 Uso diario para Fermín

### Paso 1: Abrir la carpeta de fotos
En el Escritorio, doble clic en 👉 **`📸 FOTOS DE MI WEB`**.

Verás una carpeta por galería:
* `01_people`
* `02_nature`
* `03_rituals`
* `04_celebrations`
* `05_religion`
* `06_cities`
* `07_bw`

Para las fotos que pasan a pantalla completa en la página de inicio, usa 👉 **`🖼️ FOTOS DE LA PORTADA`**.

---

### Paso 2: Trabajar con las fotos

#### A) Añadir fotos a una galería
1. Abre la carpeta de la galería (por ejemplo, `02_nature`).
2. Pega ahí tus fotos (JPG es lo mejor; también valen PNG, TIFF y las HEIC del iPhone).
3. No te preocupes por el tamaño: al publicar, las fotos muy grandes se reducen automáticamente a tamaño web (3000 píxeles) **dentro de esta carpeta**. Tus originales de la cámara o de Lightroom no se tocan, así que guárdalos donde siempre.

Los archivos que no son fotos (vídeos, documentos, RAW como `.CR2` o `.NEF`) no se publican: el botón te avisa de ellos.

#### B) Crear una galería nueva
1. Crea una carpeta nueva dentro de `📸 FOTOS DE MI WEB`.
2. Ponle un número y el nombre (por ejemplo `08_japón` o `08_retratos`). El número decide su posición en el menú; el nombre es lo que se ve en el menú (en mayúsculas).
3. Pega las fotos dentro. Las fotos deben ir directamente en la carpeta de la galería, no en subcarpetas.

#### C) Retirar una foto
Bórrala de su carpeta. Al publicar desaparece de la web por completo.

#### D) Orden y títulos
* **Orden:** si quieres que unas fotos salgan las primeras y en un orden concreto, ponles un número delante: `01_pescador.jpg`, `02_templo.jpg`... El resto va detrás: primero las que ya estaban en la web antigua, en su orden de siempre, y luego las demás por nombre.
* **Títulos:** si pones título a la foto en Lightroom (campo *Título*), se usa ese. Si no, se usa el nombre del archivo sin el número (`01_Pescador_en_el_rio.jpg` → *Pescador en el rio*).
* **Cuidado al renombrar galerías:** cambiar solo el número (`02_nature` → `05_nature`) es seguro. Cambiar la palabra (`nature` → `naturaleza`) cambia la dirección de esa galería en internet.

---

### Paso 3: Publicar
Cuando hayas terminado, doble clic en 👉 **`🚀 ACTUALIZAR MI WEB`**.

Se abre una ventana que:
1. Revisa tus fotos (y reduce las grandes).
2. Guarda los cambios.
3. Los sube a internet.
4. **Espera a que la web se actualice** (normalmente entre 2 y 5 minutos) y te lo confirma.

Lo que puedes ver al final:
* 🟢 **¡TODO LISTO! TUS FOTOS YA ESTÁN EN LA WEB** — Perfecto. Si debajo aparece algún aviso en amarillo (por ejemplo, una foto dañada), esa foto concreta no se ha publicado.
* 🟡 **TUS FOTOS ESTÁN SUBIDAS, PERO LA WEB AÚN NO HA CAMBIADO** — Mira la web un poco más tarde. Si al día siguiente sigue igual, avisa a Iñigo.
* 🔴 **NO SE HA PUBLICADO: ...** — Lee el mensaje: normalmente es que no hay internet. Tus fotos no se pierden; vuelve a pulsar el icono más tarde. Si se repite, avisa a Iñigo (el detalle técnico en gris es para él).

Puedes cerrar la ventana cuando quieras: lo que ya se ha subido se publica igualmente.

---

### Paso 4: Comprobar la web
Abre 🌐 **[https://ferminezcurdia.com](https://ferminezcurdia.com)**. Si no ves los cambios, recarga la página con `Ctrl + F5` (Windows) o `Cmd + Mayúsculas + R` (Mac).
