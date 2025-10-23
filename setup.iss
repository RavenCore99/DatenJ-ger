[Setup]
AppName=DatenJäger
AppVersion=Alpha V.1 Launch Test
DefaultDirName={pf}\DatenJäger
OutputDir=Output
OutputBaseFilename=setup
Compression=lzma
SetupIconFile=logo.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\GestorPDFs.exe"; DestDir: "{app}"
Source: "base_datos_pdfs.db"; DestDir: "{app}"
Source: "logo.png"; DestDir: "{app}"

[Icons]
Name: "{group}\DatenJäger"; Filename: "{app}\GestorPDFs.exe"

[Run]
Filename: "{app}\GestorPDFs.exe"
