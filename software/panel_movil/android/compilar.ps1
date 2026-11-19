param(
    [string]$Sdk = (Join-Path $env:USERPROFILE 'AppData/Local/Android/Sdk'),
    [string]$Salida = (Join-Path $PSScriptRoot 'build')
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$tools = (Get-ChildItem "$Sdk/build-tools" -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
$platform = (Get-ChildItem "$Sdk/platforms" -Recurse -Filter android.jar | Sort-Object FullName -Descending | Select-Object -First 1).FullName
New-Item -ItemType Directory -Force $Salida | Out-Null
$Salida = (Resolve-Path $Salida).Path
$tmp = Join-Path $Salida ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Force "$tmp/classes","$tmp/dex" | Out-Null
& javac --release 8 -encoding UTF-8 -classpath $platform -d "$tmp/classes" (Get-ChildItem "$PSScriptRoot/*.java").FullName
& jar --create --file "$tmp/classes.jar" -C "$tmp/classes" .
& "$tools/d8.bat" --min-api 23 --lib $platform --output "$tmp/dex" "$tmp/classes.jar"
& "$tools/aapt2.exe" link -o "$tmp/base.apk" -I $platform --manifest "$PSScriptRoot/AndroidManifest.xml"
Copy-Item "$tmp/base.apk" "$tmp/unsigned.apk"
# Agregar classes.dex en la raíz del APK antes de alinear y firmar.
& jar --update --file "$tmp/unsigned.apk" -C "$tmp/dex" classes.dex
& "$tools/zipalign.exe" -f 4 "$tmp/unsigned.apk" "$tmp/aligned.apk"
$clave = Join-Path $Salida 'lumi-debug.jks'
if (!(Test-Path $clave)) {
    & keytool -genkeypair -keystore $clave -storepass android -keypass android -alias lumi-debug -dname 'CN=LUMI Debug' -keyalg RSA -keysize 2048 -validity 3650
}
& "$tools/apksigner.bat" sign --ks $clave --ks-pass pass:android --key-pass pass:android --out "$Salida/LUMI-Banco.apk" "$tmp/aligned.apk"
& "$tools/apksigner.bat" verify "$Salida/LUMI-Banco.apk"
Write-Output "$Salida/LUMI-Banco.apk"
