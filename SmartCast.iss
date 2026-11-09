; SmartCast Windows 安装包脚本 (Inno Setup 7)

#define MyAppName "SmartCast"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SmartCast"
#define MyAppExeName "SmartCast.exe"

[Setup]
AppId={{8E6F3A12-9C4B-4E8D-A1D5-5C8B21A9F042}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayName={#MyAppName} 卸载
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=build\LICENSE.txt
SetupIconFile=resources\assets\app-icon.ico
OutputDir=dist
OutputBaseFilename=SmartCastSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog commandline
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:";

[Files]
Source: "dist\SmartCast\*"; DestDir: "{app}"; Excludes: "resources\picture\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\resources\assets\app-icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\resources\assets\app-icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\logs"


