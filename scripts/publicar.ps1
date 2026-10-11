# Publica en ferminezcurdia.com las fotos de la carpeta content/.
# Lo lanza PUBLICAR_WEB.bat (icono "ACTUALIZAR MI WEB" del Escritorio).
# Todo lo que se muestra en pantalla va dirigido a Fermín: castellano llano.
#
# Pasos: preparar fotos (reducir originales grandes) -> guardar (commit) ->
# traer cambios de Iñigo (rebase) -> subir (push) -> esperar a que la web
# muestre la nueva versión (estado-publicacion.json).

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Repo

$Web = 'https://ferminezcurdia.com'
if ($env:FERMIN_WEB_URL) { $Web = $env:FERMIN_WEB_URL }   # solo para pruebas
$Rama = 'main'
$LadoMaximo = 3000          # píxeles del lado largo; la web muestra como mucho 2560
$TamanoMaximoMB = 45        # GitHub rechaza archivos de más de 100 MB
$MinutosEspera = 12
if ($env:FERMIN_MINUTOS_ESPERA) { $MinutosEspera = [double]$env:FERMIN_MINUTOS_ESPERA }   # solo para pruebas
$EsperarPulsacion = -not $env:FERMIN_SIN_PAUSA   # las pruebas automáticas no pulsan teclas

function Linea { Write-Host '======================================================' }
function Paso($texto) { Write-Host ''; Write-Host $texto -ForegroundColor Cyan }
function Info($texto) { Write-Host "   $texto" }
function Aviso($texto) { Write-Host "   $texto" -ForegroundColor Yellow }

function Terminar($codigo) {
    Write-Host ''
    if ($EsperarPulsacion) {
        Write-Host 'Pulsa cualquier tecla para cerrar esta ventana...'
        try { [void]$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } catch { [void](Read-Host) }
    }
    exit $codigo
}

function Fallo($titulo, $explicacion, $detalle) {
    Write-Host ''
    Linea
    Write-Host "  NO SE HA PUBLICADO: $titulo" -ForegroundColor Red
    Linea
    foreach ($l in $explicacion) { Write-Host "  $l" }
    if ($detalle) {
        Write-Host ''
        Write-Host '  Detalle técnico (para Iñigo):' -ForegroundColor DarkGray
        foreach ($l in ($detalle -split "`n")) { if ($l.Trim()) { Write-Host "    $l" -ForegroundColor DarkGray } }
    }
    Terminar 1
}

# Ejecuta git y devuelve @{ Codigo; Texto } sin que los mensajes de git se vean como errores
function GitR {
    $salida = & git @args 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -ne 'System.Management.Automation.RemoteException' }
    return @{ Codigo = $LASTEXITCODE; Texto = (($salida | Out-String).Trim()) }
}

# Cómo ve Fermín una ruta: «08_japon/foto.jpg» o «portada/foto.jpg»
function Ruta-Amable($rel) {
    return ($rel -replace '^content/galleries/', '' -replace '^content/home_slides/', 'portada/' -replace '^content/', '')
}

function ListaGit($argumentos) {
    $r = GitR @argumentos
    if ($r.Codigo -ne 0 -or -not $r.Texto) { return @() }
    return @($r.Texto -split "`0" | ForEach-Object { $_.Trim("`r", "`n") } | Where-Object { $_ })
}

Clear-Host
Linea
Write-Host '         PORTFOLIO WEB - FERMÍN EZCURDIA'
Linea

# --- 0. Comprobaciones -------------------------------------------------------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fallo 'falta un programa' @('Git no está instalado en este ordenador.', 'Avisa a Iñigo para que lo instale.')
}
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    Fallo 'la carpeta de la web no está bien instalada' @('Avisa a Iñigo.') "No hay repositorio git en $Repo"
}

# Si una publicación anterior se quedó a medias, deshacerla (no se pierde ninguna foto)
if ((Test-Path (Join-Path $Repo '.git/rebase-merge')) -or (Test-Path (Join-Path $Repo '.git/rebase-apply'))) {
    [void](GitR rebase --abort)
}

$rama = (GitR rev-parse --abbrev-ref HEAD).Texto
if ($rama -ne $Rama) {
    Fallo 'la carpeta de la web no está en su estado normal' @('Avisa a Iñigo.') "Rama actual: $rama (se esperaba $Rama)"
}

# Sin nombre y correo, git no puede guardar los cambios: se configuran solos
if (-not (GitR config user.name).Texto) { [void](GitR config user.name 'Fermín Ezcurdia') }
if (-not (GitR config user.email).Texto) { [void](GitR config user.email 'fermin@ferminezcurdia.com') }

# --- 1. Preparar fotos -------------------------------------------------------
Paso '[1/4] Revisando tus fotos...'

$nuevas = ListaGit @('-c', 'core.quotepath=false', 'ls-files', '-z', '--others', '--modified', '--exclude-standard', '--', 'content')
$nuevas = @($nuevas | Select-Object -Unique | Where-Object { Test-Path -LiteralPath (Join-Path $Repo $_) -PathType Leaf })

$dibujo = $true
try { Add-Type -AssemblyName System.Drawing -ErrorAction Stop; (New-Object Drawing.Bitmap(1, 1)).Dispose() } catch { $dibujo = $false }

function Reducir-Foto($ruta) {
    # Devuelve la ruta final de la foto (cambia si un TIFF/BMP se convierte en JPG)
    $ext = [IO.Path]::GetExtension($ruta).ToLower()
    $convertir = $ext -in @('.tif', '.tiff', '.bmp')
    if ($ext -notin @('.jpg', '.jpeg', '.png') -and -not $convertir) { return $ruta }
    if (-not $dibujo) { return $ruta }

    $img = $null; $bmp = $null; $g = $null; $ms = $null
    try {
        $ms = New-Object IO.MemoryStream(, [IO.File]::ReadAllBytes($ruta))
        # Sin aplicar el perfil de color: se conserva tal cual y la web lo convierte después
        $img = [Drawing.Image]::FromStream($ms, $false, $false)
        $lado = [Math]::Max($img.Width, $img.Height)
        if ($lado -le $LadoMaximo -and -not $convertir) { return $ruta }

        $f = [Math]::Min(1.0, $LadoMaximo / $lado)
        $w = [int][Math]::Max(1, [Math]::Round($img.Width * $f))
        $h = [int][Math]::Max(1, [Math]::Round($img.Height * $f))
        $formatoPixel = if ($ext -eq '.png') { [Drawing.Imaging.PixelFormat]::Format32bppArgb } else { [Drawing.Imaging.PixelFormat]::Format24bppRgb }
        $bmp = New-Object Drawing.Bitmap($w, $h, $formatoPixel)
        $bmp.SetResolution($img.HorizontalResolution, $img.VerticalResolution)
        $g = [Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.CompositingQuality = [Drawing.Drawing2D.CompositingQuality]::HighQuality
        $g.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::HighQuality
        $attr = New-Object Drawing.Imaging.ImageAttributes
        $attr.SetWrapMode([Drawing.Drawing2D.WrapMode]::TileFlipXY)
        $g.DrawImage($img, (New-Object Drawing.Rectangle(0, 0, $w, $h)), 0, 0, $img.Width, $img.Height, [Drawing.GraphicsUnit]::Pixel, $attr)
        # Conservar los datos de la foto (orientación, título, perfil de color...)
        foreach ($p in $img.PropertyItems) { try { $bmp.SetPropertyItem($p) } catch {} }

        $destino = $ruta
        if ($convertir) {
            $base = [IO.Path]::Combine([IO.Path]::GetDirectoryName($ruta), [IO.Path]::GetFileNameWithoutExtension($ruta))
            $destino = "$base.jpg"; $n = 2
            while (Test-Path -LiteralPath $destino) { $destino = "$base-$n.jpg"; $n++ }
        }
        $temporal = "$destino.tmp"
        if ($ext -eq '.png') {
            $bmp.Save($temporal, [Drawing.Imaging.ImageFormat]::Png)
        } else {
            $codec = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
            $params = New-Object Drawing.Imaging.EncoderParameters(1)
            $params.Param[0] = New-Object Drawing.Imaging.EncoderParameter([Drawing.Imaging.Encoder]::Quality, [long]92)
            $bmp.Save($temporal, $codec, $params)
        }
        $g.Dispose(); $g = $null; $bmp.Dispose(); $bmp = $null; $img.Dispose(); $img = $null
        Move-Item -LiteralPath $temporal -Destination $destino -Force
        if ($convertir) { Remove-Item -LiteralPath $ruta -Force }
        $script:reducidas++
        return $destino
    } catch {
        Aviso "No se ha podido reducir «$([IO.Path]::GetFileName($ruta))»; se subirá tal cual."
        return $ruta
    } finally {
        if ($g) { $g.Dispose() }; if ($bmp) { $bmp.Dispose() }; if ($img) { $img.Dispose() }; if ($ms) { $ms.Dispose() }
    }
}

$reducidas = 0
foreach ($rel in $nuevas) { [void](Reducir-Foto (Join-Path $Repo $rel)) }
if (-not $dibujo -and $nuevas.Count) { Aviso 'No se han podido reducir las fotos grandes en este ordenador; se suben tal cual.' }
if ($reducidas) { Info "$reducidas foto(s) reducidas a tamaño web (las originales de tu cámara o Lightroom no se tocan)." }

# Archivos que no son fotos: no se publican, pero se avisa
$ignorados = ListaGit @('-c', 'core.quotepath=false', 'ls-files', '-z', '--others', '--ignored', '--exclude-standard', '--', 'content')
$ignorados = @($ignorados | Where-Object { (Split-Path $_ -Leaf) -notmatch '^(\.DS_Store|Thumbs\.db|desktop\.ini|.*\.tmp)$' })
if ($ignorados.Count) {
    Aviso 'Estos archivos no son fotos que la web pueda mostrar y NO se publican:'
    foreach ($i in $ignorados) {
        $nota = if ($i -match '\.(cr2|cr3|nef|arw|dng|raf|orf|rw2|pef|srw)$') { ' (es un RAW: expórtalo como JPG)' } else { '' }
        Aviso "   - $(Ruta-Amable $i)$nota"
    }
}

[void](GitR add -A -- content)

# Archivos enormes: GitHub no los acepta, se quedan fuera
$preparados = ListaGit @('-c', 'core.quotepath=false', 'diff', '--cached', '--name-only', '-z', '--diff-filter=AM')
foreach ($rel in $preparados) {
    $ruta = Join-Path $Repo $rel
    if ((Test-Path -LiteralPath $ruta) -and ((Get-Item -LiteralPath $ruta).Length -gt $TamanoMaximoMB * 1MB)) {
        [void](GitR reset -q -- $rel)
        Aviso "«$(Ruta-Amable $rel)» es demasiado grande y NO se publica. Expórtala más pequeña (JPG)."
    }
}

# --- 2. Guardar los cambios --------------------------------------------------
Paso '[2/4] Guardando los cambios...'
$hayCambios = (GitR diff --cached --quiet).Codigo -ne 0
if ($hayCambios) {
    $fecha = Get-Date -Format 'dd/MM/yyyy HH:mm'
    $r = GitR commit -q -m "Fotos actualizadas el $fecha"
    if ($r.Codigo -ne 0) {
        Fallo 'no se han podido guardar los cambios' @('Tus fotos siguen en la carpeta, no se ha perdido nada.', 'Avisa a Iñigo.') $r.Texto
    }
    $altas = @(GitR diff --name-only --diff-filter=AM HEAD~1 HEAD -- content).Texto -split "`n" | Where-Object { $_ }
    $bajas = @(GitR diff --name-only --diff-filter=D HEAD~1 HEAD -- content).Texto -split "`n" | Where-Object { $_ }
    Info "Fotos nuevas o cambiadas: $(@($altas).Count)   Fotos retiradas: $(@($bajas).Count)"
}

# --- 3. Subir ----------------------------------------------------------------
Paso '[3/4] Subiendo a internet...'
$r = GitR fetch -q origin $Rama
if ($r.Codigo -ne 0) {
    Fallo 'no hay conexión con GitHub' @('Comprueba que tienes internet y vuelve a pulsar el icono.', 'Tus cambios están guardados y se subirán la próxima vez.') $r.Texto
}

$pendientes = [int](GitR rev-list --count "origin/$Rama..HEAD").Texto
$atrasados = [int](GitR rev-list --count "HEAD..origin/$Rama").Texto

if ($pendientes -eq 0) {
    # Nada que subir: ponerse al día con lo último de la web y salir
    if ($atrasados -gt 0) { [void](GitR merge -q --ff-only "origin/$Rama") }
    Write-Host ''
    Linea
    Write-Host '  No has añadido, cambiado ni borrado fotos.' -ForegroundColor Yellow
    Linea
    Write-Host '  Para publicar fotos:'
    Write-Host '   1. Abre el icono "FOTOS DE MI WEB" (o "FOTOS DE LA PORTADA").'
    Write-Host '   2. Pega tus fotos en la galería que quieras.'
    Write-Host '   3. Vuelve a hacer doble clic en "ACTUALIZAR MI WEB".'
    Terminar 0
}

if ($atrasados -gt 0) {
    # Iñigo ha cambiado algo de la web: traerlo y colocar las fotos encima
    $r = GitR rebase -q --autostash "origin/$Rama"
    if ($r.Codigo -ne 0) {
        [void](GitR rebase --abort)
        Fallo 'Iñigo ha cambiado lo mismo que tú a la vez' @('Tus fotos están guardadas en tu ordenador, no se ha perdido nada.', 'Avisa a Iñigo para que lo junte; después vuelve a pulsar el icono.') $r.Texto
    }
}

$r = GitR push -q origin "HEAD:$Rama"
if ($r.Codigo -ne 0) {
    $t = $r.Texto
    if ($t -match 'Authentication|403|denied|could not read Username|Permission|401') {
        Fallo 'GitHub no ha aceptado tu usuario' @('Tus cambios están guardados en tu ordenador.', 'Avisa a Iñigo para que revise el acceso a GitHub.') $t
    } elseif ($t -match 'resolve host|unable to access|timed out|Could not connect|network|Connection') {
        Fallo 'no hay conexión con GitHub' @('Comprueba que tienes internet y vuelve a pulsar el icono.', 'Tus cambios están guardados y se subirán la próxima vez.') $t
    } else {
        Fallo 'GitHub no ha aceptado la subida' @('Tus cambios están guardados en tu ordenador.', 'Vuelve a pulsar el icono; si vuelve a fallar, avisa a Iñigo.') $t
    }
}
$miVersion = (GitR rev-parse HEAD).Texto

# --- 4. Esperar a que la web se actualice ------------------------------------
Paso '[4/4] Esperando a que la web se actualice (suele tardar entre 2 y 5 minutos)...'
Info 'Puedes cerrar esta ventana si quieres: la web se actualizará igualmente.'

function Version-Publicada {
    try {
        $url = "$Web/estado-publicacion.json?t=$([DateTime]::UtcNow.Ticks)"
        return Invoke-RestMethod -Uri $url -Headers @{ 'Cache-Control' = 'no-cache' } -TimeoutSec 20
    } catch { return $null }
}

$limite = (Get-Date).AddMinutes($MinutosEspera)
$publicado = $null
$yaDescargado = $false
while ((Get-Date) -lt $limite) {
    $estado = Version-Publicada
    if ($estado -and $estado.commit) {
        if ($estado.commit -eq $miVersion) { $publicado = $estado; break }
        # La web puede tener ya una versión posterior que incluye la nuestra
        if ((GitR merge-base --is-ancestor $miVersion $estado.commit).Codigo -eq 0) { $publicado = $estado; break }
        if (-not $yaDescargado -and (GitR cat-file -e "$($estado.commit)^{commit}").Codigo -ne 0) {
            [void](GitR fetch -q origin $Rama); $yaDescargado = $true
            if ((GitR merge-base --is-ancestor $miVersion $estado.commit).Codigo -eq 0) { $publicado = $estado; break }
        }
    }
    Write-Host '.' -NoNewline
    Start-Sleep -Seconds 15
}
Write-Host ''

if (-not $publicado) {
    Write-Host ''
    Linea
    Write-Host '  TUS FOTOS ESTÁN SUBIDAS, PERO LA WEB AÚN NO HA CAMBIADO' -ForegroundColor Yellow
    Linea
    Write-Host '  A veces tarda más de lo normal. Mira la web dentro de un rato:'
    Write-Host "  $Web"
    Write-Host '  Si mañana sigue sin verse lo nuevo, avisa a Iñigo.'
    Terminar 0
}

Write-Host ''
Linea
Write-Host '   ¡TODO LISTO! TUS FOTOS YA ESTÁN EN LA WEB' -ForegroundColor Green
Linea
Write-Host "  $Web"
Write-Host '  (si no ves los cambios, recarga la página con Ctrl + F5)'
$avisos = @($publicado.avisos)
if ($avisos.Count -and $avisos[0]) {
    Write-Host ''
    Aviso 'Pero ojo, la web ha avisado de esto:'
    foreach ($a in $avisos) { Aviso " - $a" }
}
Terminar 0
