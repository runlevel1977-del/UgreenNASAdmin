; Windows-Installer (Inno Setup 6+) — liegt getrennt vom Python-Projekt unter installer/
; Build: installer\BUILD_INSTALLER.ps1 (nach python builder.py im Projektroot)

#ifndef MyAppVersion
#define MyAppVersion "23.8.0"
#endif

#define MyAppName "Ugreen NAS Admin"
#define MyAppPublisher "runlevel1977-del"
#define MyAppExeName "UgreenNASAdmin.exe"
#define MyAppURL "https://github.com/runlevel1977-del/UgreenNASAdmin"
#define MyAppUpdatesURL "https://github.com/runlevel1977-del/UgreenNASAdmin/releases"

#define MyRepoRoot ".."
#define DistExe MyRepoRoot + "\dist\" + MyAppExeName
#define RepoIcon MyRepoRoot + "\nas_icon.ico"
#define RepoLicense MyRepoRoot + "\LICENSE"

[Setup]
AppId={{9F3E8B2A-1D4C-7E60-B5A9-482C19F203E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppUpdatesURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=UgreenNASAdmin_setup_{#MyAppVersion}
SetupIconFile={#RepoIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
LicenseFile={#RepoLicense}

[Languages]
; Installer-Assistent + erste App-Sprache: Nach Setup schreibt [Code] HKCU\Software\UgreenNASAdmin
; → InstallerUiLang (de, en, hr, …). Die App liest das einmalig, wenn nas_admin_connection.json noch kein ui_lang hat.
; Alle UI-Texte sind in der EXE (Einstellungen → UI-Sprache zum Wechseln).
; Zu SUPPORTED_LANGS in ugreen_app/i18n.py: de, en, hr, fr, es, it, pl, ru, tr, ko, zh
; Kroatisch + Chinesisch (vereinfacht): Dateien unter languages_unofficial\ (von jrsoftware/issrc),
; da viele Inno-Installationen keinen Unterordner compiler:Languages\Unofficial mitliefern.
; Reihenfolge: erste Einträge haben Vorrang, wenn keine Windows-Übereinstimmung gefunden wird.
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "croatian"; MessagesFile: "languages_unofficial\Croatian.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "chinesesimplified"; MessagesFile: "languages_unofficial\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: {#DistExe}; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: string;
  LangId: string;
  DataDir: string;
  MarkerPath: string;
begin
  if CurStep <> ssPostInstall then Exit;
  { ActiveLanguage entspricht [Languages] »Name«; Groß/Kleinschreibung sicher klein.}
  LangId := LowerCase(ActiveLanguage);

  case LangId of
    'german': Code := 'de';
    'english': Code := 'en';
    'croatian': Code := 'hr';
    'french': Code := 'fr';
    'spanish': Code := 'es';
    'italian': Code := 'it';
    'polish': Code := 'pl';
    'russian': Code := 'ru';
    'turkish': Code := 'tr';
    'korean': Code := 'ko';
    'chinesesimplified': Code := 'zh';
  else
    Code := 'en';
  end;

  RegWriteStringValue(HKCU, 'Software\UgreenNASAdmin', 'InstallerUiLang', Code);

  { Zusätzlich Datei unter %LocalAppData% — schlägt bei migrierter Connection-JSON (ui_lang erzwungen »de«).}
  DataDir := ExpandConstant('{localappdata}') + '\UgreenNASAdmin';
  MarkerPath := DataDir + '\installer_selected_ui_lang.txt';
  if not DirExists(DataDir) then
    ForceDirectories(DataDir); { erstellt fehlende Teile unter localappdata }

  SaveStringToFile(MarkerPath, Code + #13#10, False);
end;
