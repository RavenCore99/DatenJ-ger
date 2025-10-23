[Setup]
AppName=Gestor de PDFs
AppVersion=1.0
DefaultDirName={pf}\Gestor de PDFs
DefaultGroupName=Gestor de PDFs
OutputDir=Output
OutputBaseFilename=setup
Compression=lzma
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\GestorPDFs.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "dist\GestorPDFs.exe"; DestDir: "{app}"
Source: "base_datos_pdfs.db"; DestDir: "{app}"
Source: "logo.png"; DestDir: "{app}"

[Icons]
Name: "{group}\Gestor de PDFs"; Filename: "{app}\GestorPDFs.exe"; IconFilename: "logo.ico"
Name: "{userdesktop}\Gestor de PDFs"; Filename: "{app}\GestorPDFs.exe"; IconFilename: "logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\GestorPDFs.exe"; Description: "Abrir Gestor de PDFs"; Flags: nowait postinstall skipifsilent
