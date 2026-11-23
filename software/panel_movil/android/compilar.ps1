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
# Artefacto nativo oficial del SDK, fijado por version y SHA-256.
$version = '150.7871.08'
$deps = Join-Path $Salida "deps/webrtc-$version"
$aar = Join-Path $Salida "deps/android-$version.aar"
New-Item -ItemType Directory -Force (Split-Path $aar) | Out-Null
if (!(Test-Path $aar)) {
    Invoke-WebRequest "https://repo.maven.apache.org/maven2/io/github/webrtc-sdk/android/$version/android-$version.aar" -OutFile $aar
}
$expected = '05f20dac7586b99e148258d43fb1cecb6c308a888de1621e473cc12f5e09109f'
if ((Get-FileHash -LiteralPath $aar -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'El AAR WebRTC no coincide con el SHA-256 esperado.'
}
# Extraer siempre el AAR verificado a una carpeta nueva; no reutilizar clases modificadas.
$deps = Join-Path $tmp 'webrtc'
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($aar, $deps)
$webRtcClasses = Join-Path $deps 'classes.jar'
& javac --release 8 -encoding UTF-8 -classpath "$platform;$webRtcClasses" -d "$tmp/classes" (Get-ChildItem "$PSScriptRoot/*.java").FullName
& jar --create --file "$tmp/classes.jar" -C "$tmp/classes" .
& "$tools/d8.bat" --min-api 23 --lib $platform --output "$tmp/dex" "$tmp/classes.jar" $webRtcClasses
& "$tools/aapt2.exe" link -o "$tmp/base.apk" -I $platform --manifest "$PSScriptRoot/AndroidManifest.xml"
Copy-Item "$tmp/base.apk" "$tmp/unsigned.apk"
New-Item -ItemType Directory -Force "$tmp/package/lib","$tmp/package/assets/licenses" | Out-Null
Copy-Item "$deps/jni/*" "$tmp/package/lib" -Recurse
Copy-Item "$PSScriptRoot/licenses/*" "$tmp/package/assets/licenses"
& jar --update --file "$tmp/unsigned.apk" -C "$tmp/dex" . -C "$tmp/package" .
& "$tools/zipalign.exe" -f 4 "$tmp/unsigned.apk" "$tmp/aligned.apk"
$clave = Join-Path $Salida 'lumi-debug.jks'
if (!(Test-Path $clave)) {
    & keytool -genkeypair -keystore $clave -storepass android -keypass android -alias lumi-debug -dname 'CN=LUMI Debug' -keyalg RSA -keysize 2048 -validity 3650
}
& "$tools/apksigner.bat" sign --ks $clave --ks-pass pass:android --key-pass pass:android --out "$Salida/LUMI-Banco.apk" "$tmp/aligned.apk"
& "$tools/apksigner.bat" verify "$Salida/LUMI-Banco.apk"
Write-Output "$Salida/LUMI-Banco.apk"
