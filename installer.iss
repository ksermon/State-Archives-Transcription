; ------- installer.iss -------
#define AppName "State Archives Transcription"
#define AppExeName "StateArchivesTranscription.exe"
#define Company "StateRecordsWA"
#define AppVersion "1.0.0"

[Setup]
AppId={{8C5E7F2F-2C9E-4B0A-9B0D-DAF8A1F6B0C1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#Company}
DefaultDirName={pf}\{#AppName}
DisableDirPage=yes
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=StateArchivesTranscription-Setup
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Dirs]
Name: "{commonappdata}\StateArchivesTranscription"; Flags: uninsalwaysuninstall

[Files]
Source: "dist\StateArchivesTranscription.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  GeminiPage: TWizardPage;
  UseGeminiCheck: TNewCheckBox;
  ApiKeyEdit: TNewEdit;
  TipText: TNewStaticText;

procedure UseGeminiCheckClick(Sender: TObject);
begin
  ApiKeyEdit.Enabled := UseGeminiCheck.Checked;
end;

procedure InitializeWizard;
begin
  GeminiPage := CreateCustomPage(wpSelectTasks, 'Gemini (Google AI) Setup', 'Optional configuration for Gemini');

  UseGeminiCheck := TNewCheckBox.Create(GeminiPage);
  UseGeminiCheck.Parent := GeminiPage.Surface;
  UseGeminiCheck.Caption := 'Use Gemini (Google AI) for transcription';
  UseGeminiCheck.Checked := False;
  UseGeminiCheck.OnClick := @UseGeminiCheckClick;

  TipText := TNewStaticText.Create(GeminiPage);
  TipText.Parent := GeminiPage.Surface;
  TipText.AutoSize := True;
  TipText.Top := UseGeminiCheck.Top + UseGeminiCheck.Height + ScaleY(8);
  TipText.Caption := 'If unchecked, the app uses built-in OCR. You can add a key later.';

  ApiKeyEdit := TNewEdit.Create(GeminiPage);
  ApiKeyEdit.Parent := GeminiPage.Surface;
  ApiKeyEdit.Top := TipText.Top + TipText.Height + ScaleY(18);
  ApiKeyEdit.Width := ScaleX(360);
  ApiKeyEdit.Text := '';
  ApiKeyEdit.Enabled := False;
  ApiKeyEdit.PasswordChar := '*';  // <-- mask input
  with TNewStaticText.Create(GeminiPage) do
  begin
    Parent := GeminiPage.Surface;
    Caption := 'Google AI API Key:';
    Left := ApiKeyEdit.Left;
    Top := ApiKeyEdit.Top - ScaleY(18);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = GeminiPage.ID) and UseGeminiCheck.Checked then
  begin
    if Trim(ApiKeyEdit.Text) = '' then
    begin
      MsgBox('Please enter your Google AI API Key or uncheck "Use Gemini".', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath, EnvContent, UseGeminiVal, ApiKeyVal: string;
begin
  if CurStep = ssPostInstall then
  begin
    UseGeminiVal := 'false';
    ApiKeyVal := '';
    if UseGeminiCheck.Checked then
    begin
      UseGeminiVal := 'true';
      ApiKeyVal := Trim(ApiKeyEdit.Text);
    end;

    EnvContent :=
      'USE_GEMINI=' + UseGeminiVal + #13#10 +
      'GOOGLE_AI_API_KEY=' + ApiKeyVal + #13#10 +
      'FLASK_ENV=production' + #13#10 +
      'HOST=127.0.0.1' + #13#10 +
      'PORT=5000' + #13#10;

    EnvPath := ExpandConstant('{commonappdata}\StateArchivesTranscription\.env');
    if not DirExists(ExtractFileDir(EnvPath)) then
      ForceDirectories(ExtractFileDir(EnvPath));
    SaveStringToFile(EnvPath, EnvContent, False);
  end;
end;