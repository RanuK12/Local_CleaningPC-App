#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Script de Saneamiento y Optimización Profesional para Windows
.DESCRIPTION
    Realiza auditoría de salud, limpieza profunda y optimización del sistema
    con protección estricta de archivos críticos y carpetas del usuario.
.AUTHOR
    Sistema de Optimización Local - v2.0
.DATE
    2026-01-16
.NOTES
    REQUIERE EJECUTARSE COMO ADMINISTRADOR
#>

#region ==================== CONFIGURACIÓN INICIAL ====================

# Configurar codificación para caracteres especiales
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"

# Colores para output
function Write-Header { param($text) Write-Host "`n$('='*70)" -ForegroundColor Cyan; Write-Host "  $text" -ForegroundColor Cyan; Write-Host "$('='*70)" -ForegroundColor Cyan }
function Write-Success { param($text) Write-Host "  [OK] $text" -ForegroundColor Green }
function Write-Warning { param($text) Write-Host "  [!] $text" -ForegroundColor Yellow }
function Write-Error { param($text) Write-Host "  [X] $text" -ForegroundColor Red }
function Write-Info { param($text) Write-Host "  [i] $text" -ForegroundColor White }
function Write-Action { param($text) Write-Host "  >>> $text" -ForegroundColor Magenta }

# Variables globales de seguimiento
$Script:TotalSpaceRecovered = 0
$Script:CleanupReport = @()
$Script:StartTime = Get-Date
$Script:InitialFreeSpace = (Get-PSDrive C).Free

#endregion

#region ==================== WHITELIST DE PROTECCIÓN ====================

$PROTECTED_PATHS = @(
    # === BIBLIOTECAS DE JUEGOS ===
    "C:\Program Files (x86)\Steam",
    "C:\Program Files\Steam",
    "C:\SteamLibrary",
    "D:\SteamLibrary",
    "E:\SteamLibrary",
    "C:\Program Files\Epic Games",
    "C:\Program Files (x86)\Epic Games",
    "D:\Epic Games",
    "C:\Program Files\WindowsApps",
    "C:\XboxGames",
    "D:\XboxGames",
    "C:\Program Files (x86)\Origin Games",
    "C:\Program Files\Origin Games",
    "C:\Program Files (x86)\Ubisoft",
    "C:\Program Files\Ubisoft",
    "C:\Program Files (x86)\GOG Galaxy",
    "C:\Program Files\GOG Galaxy",
    "C:\Program Files (x86)\Battle.net",
    "C:\Program Files\Riot Games",
    
    # === DIRECTORIOS DE USUARIO CRÍTICOS ===
    "$env:USERPROFILE\Documents",
    "$env:USERPROFILE\Desktop",
    "$env:USERPROFILE\Pictures",
    "$env:USERPROFILE\Videos",
    "$env:USERPROFILE\Music",
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Proyectos",
    "$env:USERPROFILE\Projects",
    "$env:USERPROFILE\Workspace",
    "$env:USERPROFILE\OneDrive",
    "$env:USERPROFILE\iCloudDrive",
    "$env:USERPROFILE\.vscode",
    "$env:USERPROFILE\.git",
    "$env:USERPROFILE\.ssh",
    "$env:USERPROFILE\.aws",
    "$env:USERPROFILE\.azure",
    
    # === SISTEMA CRÍTICO ===
    "C:\Windows\System32",
    "C:\Windows\SysWOW64",
    "C:\Windows\WinSxS",
    "C:\Windows\Installer",
    "C:\Program Files\Windows Defender",
    "C:\ProgramData\Microsoft\Windows Defender",
    
    # === BASES DE DATOS Y CONFIGURACIONES ===
    "$env:LOCALAPPDATA\Microsoft\Outlook",
    "$env:APPDATA\Microsoft\Outlook",
    "$env:LOCALAPPDATA\Google\Chrome\User Data",
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Packages"
)

$PROTECTED_EXTENSIONS = @(
    ".dll", ".sys", ".exe", ".msi", ".cat", ".mui",
    ".docx", ".xlsx", ".pptx", ".pdf", ".doc", ".xls",
    ".psd", ".ai", ".indd", ".prproj", ".aep",
    ".py", ".js", ".ts", ".cs", ".cpp", ".h", ".java",
    ".sql", ".db", ".sqlite", ".mdf", ".ldf"
)

function Test-IsProtectedPath {
    param([string]$Path)
    
    foreach ($protected in $PROTECTED_PATHS) {
        $expandedProtected = [Environment]::ExpandEnvironmentVariables($protected)
        if ($Path -like "$expandedProtected*") {
            return $true
        }
    }
    return $false
}

function Test-IsProtectedFile {
    param([string]$FilePath)
    
    $extension = [System.IO.Path]::GetExtension($FilePath).ToLower()
    return $PROTECTED_EXTENSIONS -contains $extension
}

#endregion

#region ==================== FUNCIONES DE UTILIDAD ====================

function Get-FolderSize {
    param([string]$Path)
    if (Test-Path $Path) {
        return (Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue | 
                Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    }
    return 0
}

function Format-FileSize {
    param([long]$Size)
    if ($Size -gt 1GB) { return "{0:N2} GB" -f ($Size / 1GB) }
    elseif ($Size -gt 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
    elseif ($Size -gt 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
    else { return "$Size Bytes" }
}

function Add-ToReport {
    param([string]$Category, [string]$Action, [long]$SpaceRecovered)
    $Script:CleanupReport += [PSCustomObject]@{
        Categoria = $Category
        Accion = $Action
        EspacioRecuperado = Format-FileSize $SpaceRecovered
        EspacioBytes = $SpaceRecovered
    }
    $Script:TotalSpaceRecovered += $SpaceRecovered
}

function Remove-SafeFiles {
    param(
        [string]$Path,
        [string]$Filter = "*",
        [int]$OlderThanDays = 0,
        [string]$Category
    )
    
    if (-not (Test-Path $Path)) {
        Write-Warning "Ruta no existe: $Path"
        return 0
    }
    
    if (Test-IsProtectedPath $Path) {
        Write-Warning "Ruta protegida, omitiendo: $Path"
        return 0
    }
    
    $totalSize = 0
    $cutoffDate = (Get-Date).AddDays(-$OlderThanDays)
    
    try {
        $files = Get-ChildItem -Path $Path -Filter $Filter -Recurse -Force -File -ErrorAction SilentlyContinue
        
        foreach ($file in $files) {
            # Verificar protecciones
            if (Test-IsProtectedFile $file.FullName) { continue }
            if (Test-IsProtectedPath $file.DirectoryName) { continue }
            
            # Verificar antigüedad si se especificó
            if ($OlderThanDays -gt 0 -and $file.LastWriteTime -gt $cutoffDate) { continue }
            
            try {
                $fileSize = $file.Length
                Remove-Item $file.FullName -Force -ErrorAction Stop
                $totalSize += $fileSize
            }
            catch {
                # Archivo en uso o sin permisos, continuar
            }
        }
    }
    catch {
        Write-Warning "Error procesando $Path : $_"
    }
    
    return $totalSize
}

function Remove-SafeFolder {
    param(
        [string]$Path,
        [string]$Category
    )
    
    if (-not (Test-Path $Path)) { return 0 }
    if (Test-IsProtectedPath $Path) {
        Write-Warning "Carpeta protegida, omitiendo: $Path"
        return 0
    }
    
    $size = Get-FolderSize $Path
    
    try {
        Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
        return $size
    }
    catch {
        # Intentar eliminar archivos individuales
        return (Remove-SafeFiles -Path $Path -Category $Category)
    }
}

#endregion

#region ==================== FASE 1: AUDITORÍA DE SALUD ====================

function Start-HealthAudit {
    Write-Header "FASE 1: AUDITORÍA DE SALUD DEL SISTEMA"
    
    $runHealth = Read-Host "  ¿Ejecutar diagnósticos de salud? (SFC/DISM pueden tomar 15-30 min) [S/N]"
    
    if ($runHealth -eq "S" -or $runHealth -eq "s") {
        
        # SFC /SCANNOW
        Write-Action "Ejecutando System File Checker (SFC /SCANNOW)..."
        Write-Info "Esto verificará la integridad de los archivos del sistema..."
        
        $sfcResult = Start-Process -FilePath "sfc.exe" -ArgumentList "/scannow" -Wait -PassThru -NoNewWindow
        
        if ($sfcResult.ExitCode -eq 0) {
            Write-Success "SFC completado exitosamente"
            Add-ToReport -Category "Salud" -Action "SFC /SCANNOW ejecutado" -SpaceRecovered 0
        } else {
            Write-Warning "SFC encontró problemas o no pudo completarse"
        }
        
        # DISM /RestoreHealth
        Write-Action "Ejecutando DISM /Online /Cleanup-Image /RestoreHealth..."
        Write-Info "Esto reparará la imagen del sistema si hay corrupción..."
        
        $dismResult = Start-Process -FilePath "DISM.exe" -ArgumentList "/Online /Cleanup-Image /RestoreHealth" -Wait -PassThru -NoNewWindow
        
        if ($dismResult.ExitCode -eq 0) {
            Write-Success "DISM completado exitosamente"
            Add-ToReport -Category "Salud" -Action "DISM RestoreHealth ejecutado" -SpaceRecovered 0
        } else {
            Write-Warning "DISM encontró problemas o no pudo completarse"
        }
        
        # Limpiar componentes obsoletos de Windows
        Write-Action "Limpiando componentes obsoletos de Windows..."
        $dismCleanup = Start-Process -FilePath "DISM.exe" -ArgumentList "/Online /Cleanup-Image /StartComponentCleanup /ResetBase" -Wait -PassThru -NoNewWindow
        
        if ($dismCleanup.ExitCode -eq 0) {
            Write-Success "Limpieza de componentes completada"
        }
        
    } else {
        Write-Info "Omitiendo fase de auditoría de salud"
    }
}

#endregion

#region ==================== FASE 2: LIMPIEZA PROFUNDA ====================

function Start-DeepClean {
    Write-Header "FASE 2: LIMPIEZA PROFUNDA"
    
    # --- 2.1 Archivos Temporales de Usuario ---
    Write-Action "Limpiando archivos temporales de usuario..."
    
    $userTempPaths = @(
        "$env:TEMP",
        "$env:LOCALAPPDATA\Temp",
        "$env:USERPROFILE\AppData\Local\Temp"
    )
    
    $tempSize = 0
    foreach ($tempPath in $userTempPaths) {
        $size = Remove-SafeFiles -Path $tempPath -Category "Temp Usuario"
        $tempSize += $size
    }
    Write-Success "Temporales de usuario: $(Format-FileSize $tempSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Archivos temporales de usuario" -SpaceRecovered $tempSize
    
    # --- 2.2 Archivos Temporales del Sistema ---
    Write-Action "Limpiando archivos temporales del sistema..."
    
    $sysTempSize = Remove-SafeFiles -Path "C:\Windows\Temp" -Category "Temp Sistema"
    Write-Success "Temporales del sistema: $(Format-FileSize $sysTempSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Archivos temporales del sistema" -SpaceRecovered $sysTempSize
    
    # --- 2.3 Prefetch (archivos de más de 14 días) ---
    Write-Action "Limpiando caché Prefetch antigua..."
    
    $prefetchSize = Remove-SafeFiles -Path "C:\Windows\Prefetch" -Filter "*.pf" -OlderThanDays 14 -Category "Prefetch"
    Write-Success "Prefetch antiguo: $(Format-FileSize $prefetchSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Caché Prefetch (>14 días)" -SpaceRecovered $prefetchSize
    
    # --- 2.4 Caché de Windows Update ---
    Write-Action "Limpiando caché de Windows Update..."
    
    # Detener servicios de Windows Update
    Write-Info "Deteniendo servicios de Windows Update temporalmente..."
    Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
    Stop-Service -Name bits -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    $wuCacheSize = 0
    $softwareDistPath = "C:\Windows\SoftwareDistribution\Download"
    if (Test-Path $softwareDistPath) {
        $wuCacheSize = Get-FolderSize $softwareDistPath
        Get-ChildItem $softwareDistPath -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Reiniciar servicios
    Start-Service -Name wuauserv -ErrorAction SilentlyContinue
    Start-Service -Name bits -ErrorAction SilentlyContinue
    
    Write-Success "Caché Windows Update: $(Format-FileSize $wuCacheSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Caché Windows Update" -SpaceRecovered $wuCacheSize
    
    # --- 2.5 Papelera de Reciclaje ---
    Write-Action "Vaciando Papelera de Reciclaje..."
    
    $recycleBinSize = 0
    try {
        $shell = New-Object -ComObject Shell.Application
        $recycleBin = $shell.NameSpace(10)
        $items = $recycleBin.Items()
        foreach ($item in $items) {
            $recycleBinSize += $item.Size
        }
        Clear-RecycleBin -Force -ErrorAction SilentlyContinue
        Write-Success "Papelera: $(Format-FileSize $recycleBinSize) liberados"
    }
    catch {
        # Método alternativo
        $recycleBinSize = (Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        Remove-Item 'C:\$Recycle.Bin\*' -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "Papelera (alt): $(Format-FileSize $recycleBinSize) liberados"
    }
    Add-ToReport -Category "Limpieza" -Action "Papelera de Reciclaje" -SpaceRecovered $recycleBinSize
    
    # --- 2.6 Archivos de Volcado de Memoria ---
    Write-Action "Eliminando archivos de volcado de memoria (.dmp)..."
    
    $dmpLocations = @(
        "C:\Windows\Minidump",
        "C:\Windows\MEMORY.DMP",
        "C:\Windows\LiveKernelReports",
        "$env:LOCALAPPDATA\CrashDumps"
    )
    
    $dmpSize = 0
    foreach ($loc in $dmpLocations) {
        if (Test-Path $loc) {
            if ((Get-Item $loc).PSIsContainer) {
                $size = Remove-SafeFiles -Path $loc -Filter "*.dmp" -Category "Dumps"
                $dmpSize += $size
            } else {
                $size = (Get-Item $loc).Length
                Remove-Item $loc -Force -ErrorAction SilentlyContinue
                $dmpSize += $size
            }
        }
    }
    Write-Success "Volcados de memoria: $(Format-FileSize $dmpSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Archivos de volcado (.dmp)" -SpaceRecovered $dmpSize
    
    # --- 2.7 Logs Antiguos ---
    Write-Action "Limpiando logs antiguos (más de 30 días)..."
    
    $logLocations = @(
        "C:\Windows\Logs",
        "C:\Windows\Panther",
        "$env:LOCALAPPDATA\Temp\*.log"
    )
    
    $logSize = 0
    $logSize += Remove-SafeFiles -Path "C:\Windows\Logs" -Filter "*.log" -OlderThanDays 30 -Category "Logs"
    $logSize += Remove-SafeFiles -Path "C:\Windows\Logs" -Filter "*.etl" -OlderThanDays 30 -Category "Logs"
    $logSize += Remove-SafeFiles -Path "C:\Windows\Panther" -Filter "*.log" -OlderThanDays 30 -Category "Logs"
    
    Write-Success "Logs antiguos: $(Format-FileSize $logSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Logs antiguos (>30 días)" -SpaceRecovered $logSize
    
    # --- 2.8 Caché de Thumbnails ---
    Write-Action "Limpiando caché de miniaturas..."
    
    $thumbCachePath = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
    $thumbSize = Remove-SafeFiles -Path $thumbCachePath -Filter "thumbcache_*.db" -Category "Thumbnails"
    Write-Success "Caché de miniaturas: $(Format-FileSize $thumbSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Caché de miniaturas" -SpaceRecovered $thumbSize
    
    # --- 2.9 Caché de Fuentes ---
    Write-Action "Limpiando caché de fuentes..."
    
    $fontCacheSize = 0
    $fontCachePath = "C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache"
    if (Test-Path $fontCachePath) {
        Stop-Service -Name FontCache -Force -ErrorAction SilentlyContinue
        $fontCacheSize = Remove-SafeFiles -Path $fontCachePath -Category "FontCache"
        Start-Service -Name FontCache -ErrorAction SilentlyContinue
    }
    Write-Success "Caché de fuentes: $(Format-FileSize $fontCacheSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Caché de fuentes" -SpaceRecovered $fontCacheSize
    
    # --- 2.10 Archivos de Error de Windows ---
    Write-Action "Limpiando reportes de errores de Windows..."
    
    $werPaths = @(
        "C:\ProgramData\Microsoft\Windows\WER",
        "$env:LOCALAPPDATA\Microsoft\Windows\WER"
    )
    
    $werSize = 0
    foreach ($werPath in $werPaths) {
        $werSize += Remove-SafeFiles -Path $werPath -Category "WER"
    }
    Write-Success "Reportes de errores: $(Format-FileSize $werSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Windows Error Reports" -SpaceRecovered $werSize
    
    # --- 2.11 Caché de Instaladores ---
    Write-Action "Limpiando caché de instaladores huérfanos..."
    
    $installerCacheSize = 0
    $installerCachePaths = @(
        "$env:LOCALAPPDATA\Downloaded Installations",
        "C:\Windows\Downloaded Installations"
    )
    
    foreach ($path in $installerCachePaths) {
        $installerCacheSize += Remove-SafeFiles -Path $path -OlderThanDays 60 -Category "Installers"
    }
    Write-Success "Caché de instaladores: $(Format-FileSize $installerCacheSize) liberados"
    Add-ToReport -Category "Limpieza" -Action "Caché de instaladores antiguos" -SpaceRecovered $installerCacheSize
    
    # --- 2.12 Limpieza de iCloud Photos (Específico para el usuario) ---
    Write-Action "Buscando residuos de iCloud Photos..."
    
    $icloudPaths = @(
        "$env:LOCALAPPDATA\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Local\Apple Inc\iCloudPhotoLibrary",
        "$env:LOCALAPPDATA\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Local\Apple Computer\iCloudPhotos",
        "$env:LOCALAPPDATA\Apple Inc\iCloud\iCloudPhotoLibrary",
        "$env:LOCALAPPDATA\Apple Computer\iCloudPhotos"
    )
    
    $icloudSize = 0
    foreach ($path in $icloudPaths) {
        if (Test-Path $path) {
            $pathSize = Get-FolderSize $path
            if ($pathSize -gt 0) {
                Write-Info "Encontrado: $path ($(Format-FileSize $pathSize))"
                $confirm = Read-Host "  ¿Eliminar? [S/N]"
                if ($confirm -eq "S" -or $confirm -eq "s") {
                    Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                    $icloudSize += $pathSize
                }
            }
        }
    }
    
    if ($icloudSize -gt 0) {
        Write-Success "Residuos de iCloud: $(Format-FileSize $icloudSize) liberados"
        Add-ToReport -Category "Limpieza" -Action "Residuos de iCloud Photos" -SpaceRecovered $icloudSize
    } else {
        Write-Info "No se encontraron residuos significativos de iCloud Photos"
    }
}

#endregion

#region ==================== FASE 3: OPTIMIZACIÓN ADICIONAL ====================

function Start-Optimization {
    Write-Header "FASE 3: OPTIMIZACIÓN ADICIONAL"
    
    # --- 3.1 Limpiar DNS Cache ---
    Write-Action "Limpiando caché DNS..."
    ipconfig /flushdns | Out-Null
    Write-Success "Caché DNS limpiada"
    
    # --- 3.2 Limpiar ARP Cache ---
    Write-Action "Limpiando caché ARP..."
    arp -d * 2>$null
    Write-Success "Caché ARP limpiada"
    
    # --- 3.3 Ejecutar Disk Cleanup automatizado ---
    Write-Action "Ejecutando limpieza de disco automatizada..."
    
    # Configurar CleanMgr para limpieza silenciosa
    $cleanupKeys = @(
        "Active Setup Temp Folders",
        "BranchCache",
        "Downloaded Program Files",
        "Internet Cache Files",
        "Old ChkDsk Files",
        "Previous Installations",
        "Recycle Bin",
        "Setup Log Files",
        "System error memory dump files",
        "System error minidump files",
        "Temporary Files",
        "Temporary Setup Files",
        "Thumbnail Cache",
        "Update Cleanup",
        "Upgrade Discarded Files",
        "Windows Error Reporting Archive Files",
        "Windows Error Reporting Queue Files",
        "Windows ESD installation files",
        "Windows Upgrade Log Files"
    )
    
    $volumeCachesKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
    
    foreach ($key in $cleanupKeys) {
        $keyPath = Join-Path $volumeCachesKey $key
        if (Test-Path $keyPath) {
            Set-ItemProperty -Path $keyPath -Name "StateFlags0100" -Value 2 -ErrorAction SilentlyContinue
        }
    }
    
    # Ejecutar cleanmgr
    Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/sagerun:100" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    Write-Success "Limpieza de disco completada"
    Add-ToReport -Category "Optimización" -Action "Windows Disk Cleanup ejecutado" -SpaceRecovered 0
    
    # --- 3.4 Compactar sistema operativo (opcional) ---
    $compactOS = Read-Host "  ¿Compactar archivos del SO? (Ahorra ~2GB, puede tomar 10-15 min) [S/N]"
    if ($compactOS -eq "S" -or $compactOS -eq "s") {
        Write-Action "Compactando archivos del sistema operativo..."
        $compactResult = Start-Process -FilePath "compact.exe" -ArgumentList "/CompactOS:always" -Wait -PassThru -NoNewWindow
        if ($compactResult.ExitCode -eq 0) {
            Write-Success "Sistema operativo compactado"
            Add-ToReport -Category "Optimización" -Action "CompactOS aplicado" -SpaceRecovered 2GB
        }
    }
}

#endregion

#region ==================== REPORTE FINAL ====================

function Show-FinalReport {
    Write-Header "REPORTE FINAL DE SANEAMIENTO"
    
    $Script:EndTime = Get-Date
    $Script:FinalFreeSpace = (Get-PSDrive C).Free
    $Script:ActualSpaceRecovered = $Script:FinalFreeSpace - $Script:InitialFreeSpace
    $Script:Duration = $Script:EndTime - $Script:StartTime
    
    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────────────────────────────┐" -ForegroundColor White
    Write-Host "  │                    RESUMEN DE OPERACIONES                       │" -ForegroundColor White
    Write-Host "  └─────────────────────────────────────────────────────────────────┘" -ForegroundColor White
    Write-Host ""
    
    # Tabla de acciones
    Write-Host "  Categoría          Acción                                    Espacio" -ForegroundColor Cyan
    Write-Host "  ─────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
    
    foreach ($item in $Script:CleanupReport) {
        $cat = $item.Categoria.PadRight(18)
        $action = $item.Accion
        if ($action.Length -gt 38) { $action = $action.Substring(0, 35) + "..." }
        $action = $action.PadRight(38)
        $space = $item.EspacioRecuperado.PadLeft(10)
        Write-Host "  $cat $action $space" -ForegroundColor White
    }
    
    Write-Host "  ─────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
    Write-Host ""
    
    # Estadísticas finales
    Write-Host "  ┌─────────────────────────────────────────────────────────────────┐" -ForegroundColor Green
    Write-Host "  │                    ESTADÍSTICAS FINALES                         │" -ForegroundColor Green
    Write-Host "  └─────────────────────────────────────────────────────────────────┘" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "  Espacio libre ANTES:    $(Format-FileSize $Script:InitialFreeSpace)" -ForegroundColor Yellow
    Write-Host "  Espacio libre DESPUÉS:  $(Format-FileSize $Script:FinalFreeSpace)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  ESPACIO TOTAL RECUPERADO: $(Format-FileSize $Script:ActualSpaceRecovered)" -ForegroundColor Green -BackgroundColor DarkGreen
    Write-Host "  ══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Duración total: $($Script:Duration.ToString('hh\:mm\:ss'))" -ForegroundColor Gray
    Write-Host "  Fecha/Hora: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    # Guardar log
    $logPath = "$env:USERPROFILE\Desktop\Saneamiento_Log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    $logContent = @"
=========================================================
REPORTE DE SANEAMIENTO Y OPTIMIZACIÓN - WINDOWS
=========================================================
Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Duración: $($Script:Duration.ToString('hh\:mm\:ss'))
---------------------------------------------------------
Espacio libre ANTES:   $(Format-FileSize $Script:InitialFreeSpace)
Espacio libre DESPUÉS: $(Format-FileSize $Script:FinalFreeSpace)
ESPACIO RECUPERADO:    $(Format-FileSize $Script:ActualSpaceRecovered)
---------------------------------------------------------
DETALLE DE OPERACIONES:
$($Script:CleanupReport | Format-Table -AutoSize | Out-String)
=========================================================
"@
    
    $logContent | Out-File -FilePath $logPath -Encoding UTF8
    Write-Success "Log guardado en: $logPath"
}

#endregion

#region ==================== EJECUCIÓN PRINCIPAL ====================

Clear-Host
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     SISTEMA DE SANEAMIENTO Y OPTIMIZACIÓN PROFESIONAL v2.0       ║" -ForegroundColor Cyan
Write-Host "  ║                    Windows Health & Cleanup                        ║" -ForegroundColor Cyan
Write-Host "  ╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [!] Este script requiere privilegios de Administrador" -ForegroundColor Yellow
Write-Host "  [!] Se aplicarán protecciones a carpetas críticas y de juegos" -ForegroundColor Yellow
Write-Host ""

# Verificar privilegios de administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Error "Este script debe ejecutarse como Administrador"
    Write-Host ""
    Write-Host "  Haga clic derecho en PowerShell y seleccione 'Ejecutar como administrador'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presione Enter para salir"
    exit 1
}

Write-Success "Ejecutando con privilegios de Administrador"
Write-Host ""

$confirm = Read-Host "  ¿Desea iniciar el proceso de saneamiento? [S/N]"
if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Info "Operación cancelada por el usuario"
    exit 0
}

# Ejecutar fases
Start-HealthAudit
Start-DeepClean
Start-Optimization
Show-FinalReport

Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║           ¡SANEAMIENTO COMPLETADO EXITOSAMENTE!                   ║" -ForegroundColor Green
Write-Host "  ╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$restart = Read-Host "  ¿Desea reiniciar el equipo ahora para aplicar todos los cambios? [S/N]"
if ($restart -eq "S" -or $restart -eq "s") {
    Write-Info "Reiniciando en 10 segundos... (Ctrl+C para cancelar)"
    Start-Sleep -Seconds 10
    Restart-Computer -Force
}

Write-Host ""
Write-Host "  Presione Enter para cerrar..." -ForegroundColor Gray
Read-Host

#endregion
