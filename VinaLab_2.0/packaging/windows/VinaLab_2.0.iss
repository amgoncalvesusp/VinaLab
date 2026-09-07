#define AppName "VinaLab 2.0"
#define AppVersion "2.0.1"
#define AppPublisher "VinaLab"
#define AppExeName "VinaLab_2.0.exe"
#define ProjectRoot ExtractFileDir(ExtractFileDir(RemoveBackslashUnlessRoot(SourcePath)))

[Setup]
AppId={{A2C587BC-6CB8-4A4B-B6D5-4B96A4607A48}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\VinaLab 2.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultGroupName={#AppName}
OutputDir={#ProjectRoot}\release\windows
OutputBaseFilename=VinaLab_2.0.1_Setup_x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#ProjectRoot}\dist\VinaLab_2.0\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
