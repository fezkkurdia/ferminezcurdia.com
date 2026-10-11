# Configuración inicial del ordenador de Fermín (la ejecuta Iñigo una vez):
# accesos directos en el Escritorio, identidad de git y acceso a GitHub.
# Lo lanza INSTALAR_ACCESOS_DIRECTOS.bat.

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Repo

function Linea { Write-Host '======================================================' }
function Terminar($codigo) {
    Write-Host ''
    Write-Host 'Pulsa cualquier tecla para cerrar esta ventana...'
    try { [void]$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } catch { [void](Read-Host) }
    exit $codigo
}

Linea
Write-Host '   INSTALADOR DE ACCESOS DIRECTOS EN EL ESCRITORIO'
Linea
Write-Host ''

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host '[ERROR] Git no está instalado. Instálalo desde https://git-scm.com y repite.' -ForegroundColor Red
    Terminar 1
}

# 1. Identidad para guardar cambios (sin ella el botón de publicar no puede funcionar)
if (-not ((& git config user.name) 2>$null)) { & git config user.name 'Fermín Ezcurdia' }
if (-not ((& git config user.email) 2>$null)) { & git config user.email 'fermin@ferminezcurdia.com' }
Write-Host "[OK] Los cambios se guardarán a nombre de: $(& git config user.name) <$(& git config user.email)>" -ForegroundColor Green

# 2. Accesos directos (sin emojis en el nombre: WScript.Shell no sabe guardarlos)
try {
    $escritorio = [Environment]::GetFolderPath('Desktop')
    $ws = New-Object -ComObject WScript.Shell

    $accesos = @(
        @{ Nombre = 'FOTOS DE MI WEB'; Destino = (Join-Path $Repo 'content\galleries'); Icono = 'shell32.dll,3' },
        @{ Nombre = 'FOTOS DE LA PORTADA'; Destino = (Join-Path $Repo 'content\home_slides'); Icono = 'shell32.dll,3' },
        @{ Nombre = 'ACTUALIZAR MI WEB'; Destino = (Join-Path $Repo 'PUBLICAR_WEB.bat'); Icono = 'imageres.dll,229' }
    )
    foreach ($a in $accesos) {
        $s = $ws.CreateShortcut((Join-Path $escritorio "$($a.Nombre).lnk"))
        $s.TargetPath = $a.Destino
        $s.WorkingDirectory = $Repo
        $s.IconLocation = $a.Icono
        $s.Save()
        Write-Host "[OK] Acceso directo creado: $($a.Nombre)" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] No se pudieron crear los accesos directos: $_" -ForegroundColor Red
    Terminar 1
}

# 3. Acceso a GitHub: la primera vez se abre una ventana para iniciar sesión.
#    La contraseña queda guardada en Windows y Fermín no vuelve a verla.
Write-Host ''
Write-Host 'Comprobando el acceso a GitHub (si se abre una ventana, inicia sesión)...'
$salida = & git push --dry-run origin HEAD:main 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -eq 0) {
    Write-Host '[OK] Este ordenador puede publicar en la web.' -ForegroundColor Green
} else {
    Write-Host '[ERROR] Este ordenador todavía no puede publicar en GitHub:' -ForegroundColor Red
    $salida | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
    Write-Host 'Inicia sesión con una cuenta de GitHub con permiso de escritura en el repositorio y repite.'
    Terminar 1
}

Write-Host ''
Linea
Write-Host '           ¡INSTALACIÓN COMPLETADA!' -ForegroundColor Green
Linea
Write-Host ''
Write-Host 'En el Escritorio tienes:'
Write-Host '  1. FOTOS DE MI WEB      (galerías: pegar o borrar fotos)'
Write-Host '  2. FOTOS DE LA PORTADA  (fotos que pasan en la página de inicio)'
Write-Host '  3. ACTUALIZAR MI WEB    (publicar los cambios)'
Terminar 0
