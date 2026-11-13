; Inno Setup script for AutoShorts. Built by .github/workflows/build-windows.yml
#define AppVer GetEnv("APP_VERSION")
#if AppVer == ""
  #define AppVer "1.0.0"
#endif

[Setup]
AppId={{6D2B7E41-3C9A-4F5E-9B21-7A8C4D1E2F30}
AppName=AutoShorts
AppVersion={#AppVer}
AppPublisher=AutoShorts
DefaultDirName={localappdata}\AutoShorts
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=AutoShorts-Setup
SetupIconFile=..\resource\icon.ico
UninstallDisplayIcon={app}\AutoShorts.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(AddBackslash(CompilerPath) + "Languages\Arabic.isl")
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\app\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\AutoShorts"; Filename: "{app}\AutoShorts.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\AutoShorts"; Filename: "{app}\AutoShorts.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoShorts.exe"; Description: "{cm:LaunchProgram,AutoShorts}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app\__pycache__"
Type: filesandordirs; Name: "{app}\storage\cache"
