#define AppVersion "1.2.0"
[Setup]
AppId={{C1A04B2E-6235-4AE7-8DD8-C7D06725A382}
AppName=学籍报告英文助手
AppVersion={#AppVersion}
AppPublisher=CHSI PDF Translator contributors
DefaultDirName={localappdata}\Programs\CHSITranslator
DefaultGroupName=学籍报告英文助手
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\release
OutputBaseFilename=CHSI-Translator-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UninstallDisplayIcon={app}\CHSITranslator.exe
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "zhcn"; MessagesFile: "compiler:Default.isl,ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\dist\CHSITranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\学籍报告英文助手"; Filename: "{app}\CHSITranslator.exe"
Name: "{autodesktop}\学籍报告英文助手"; Filename: "{app}\CHSITranslator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CHSITranslator.exe"; Description: "{cm:LaunchProgram,学籍报告英文助手}"; Flags: nowait postinstall skipifsilent


