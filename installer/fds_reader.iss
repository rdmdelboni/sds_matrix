; Inno Setup Script for FDS Reader
#define MyAppName "FDS Reader"
#define MyAppVersion "2.1.0"
#define MyAppExeName "fds-reader.exe"

[Setup]
AppId={{B6A4A035-61B6-4E5D-9F8B-3F3E2C5E1F21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=fds-reader-setup-{#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent
