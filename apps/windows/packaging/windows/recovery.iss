// 程序文件的有限恢复协议；卸载资料选择另由 uninstall_data.iss 处理。
const
  RecoveryHeader = 'CANGOO-RECOVERY-1';
  FilesHeader = 'CANGOO-FILES-1 {#AppId}';
  RecoveryDirectory = '.cangoo-recovery';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1';
type
  TInstallVersion = array[0..2] of Integer;
var
  AppFolder, RecoveryFolder, FailureMessage: String;
  OwnTransaction, InstallCommitted, RecoveredInThisRun, IntegrityFailed: Boolean;
  ExplicitDirectory, CommitFailed: Boolean;
  ParentFolderEdit: TNewEdit;
  StartMenuChoice, DesktopChoice: TNewCheckBox;
  UninstallButton: TNewButton;
  InstallMutex, UninstallMutex: NativeInt;
  SetupOperation, InstalledVersion, MaintenanceFolder: String;

function FileAttributes(Name: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function OpenFile(Name: String; Access, Share: LongWord; Security: NativeInt;
  Creation, Flags: LongWord; Template: NativeInt): NativeInt;
  external 'CreateFileW@kernel32.dll stdcall';
function FlushFile(Handle: NativeInt): Boolean;
  external 'FlushFileBuffers@kernel32.dll stdcall';
function CloseFile(Handle: NativeInt): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function ReplaceFile(Source, Dest: String; Flags: LongWord): Boolean;
  external 'MoveFileExW@kernel32.dll stdcall';
function AcquireMutex(Security: NativeInt; InitialOwner: Boolean; Name: String): NativeInt;
  external 'CreateMutexW@kernel32.dll stdcall';
function LastWinError: LongWord;
  external 'GetLastError@kernel32.dll stdcall';

procedure Require(Condition: Boolean);
begin
  if not Condition then RaiseException(CustomMessage(FailureMessage));
end;

procedure CheckPath(Path: String);
var Attributes: LongWord; Parent: String;
begin
  // 检查整条父链，避免在提权安装中经目录联接越过所选目录。
  while Length(Path) > 3 do begin
    Attributes := FileAttributes(Path);
    Require((Attributes = $FFFFFFFF) or ((Attributes and $400) = 0));
    Parent := ExtractFileDir(Path);
    if Parent = Path then Break;
    Path := Parent;
  end;
end;

procedure ValidateRelative(Name: String);
begin
  Require((Name <> '') and (Length(Name) < 1024) and
    (Pos(':', Name) = 0) and (Pos('/', Name) = 0) and
    (Pos('..', Name) = 0) and (Pos('|', Name) = 0) and
    (Name[1] <> '\') and (Copy(Name, Length(Name), 1) <> '\'));
  Require((Name = 'Cangoo.exe') or (Name = 'cangoo_strength_worker.exe') or
    (Name = 'install_files.txt') or (Copy(Name, 1, 10) = '_internal\') or
    ((Copy(Name, 1, 5) = 'unins') and (Pos('\', Name) = 0) and
      ((ExtractFileExt(Name) = '.exe') or (ExtractFileExt(Name) = '.dat') or
       (ExtractFileExt(Name) = '.msg'))));
end;

procedure SyncFile(Path: String);
var Handle: NativeInt;
begin
  Handle := OpenFile(Path, $40000000, 1, 0, 3, $80, 0);
  Require(Handle <> -1);
  try Require(FlushFile(Handle)); finally CloseFile(Handle); end;
end;

procedure WriteState(Value: String);
var Temp: String;
begin
  Temp := RecoveryFolder + '\state.tmp';
  Require(SaveStringToFile(Temp, RecoveryHeader + #10 + Value + #10, False));
  SyncFile(Temp);
  Require(ReplaceFile(Temp, RecoveryFolder + '\state', 9));
end;

function ReadState: String;
var Value: AnsiString;
begin
  CheckPath(RecoveryFolder + '\state');
  Require(LoadStringFromFile(RecoveryFolder + '\state', Value));
  Require(Copy(Value, 1, Length(RecoveryHeader) + 1) = RecoveryHeader + #10);
  Result := Trim(Copy(Value, Length(RecoveryHeader) + 2, MaxInt));
  Require((Result = 'PREPARING') or (Result = 'READY') or
    (Result = 'COMMITTED') or (Result = 'RECOVERED'));
end;

procedure CheckProgramStopped;
var I: Integer; Name: String; Handle: NativeInt;
begin
  for I := 0 to 1 do begin
    if I = 0 then Name := 'Cangoo.exe' else Name := 'cangoo_strength_worker.exe';
    Name := AppFolder + '\' + Name;
    CheckPath(Name);
    if FileExists(Name) then begin
      // 申请写句柄但不写字节：只读句柄可能成功打开运行中的映像。
      Handle := OpenFile(Name, $40000000, 0, 0, 3, $80, 0);
      if Handle = -1 then RaiseException(CustomMessage('CloseApp'));
      CloseFile(Handle);
    end;
  end;
end;

procedure CheckTree(Path: String);
var Found: TFindRec;
begin
  CheckPath(Path);
  if FindFirst(Path + '\*', Found) then begin
    try
      repeat
        if (Found.Name <> '.') and (Found.Name <> '..') then begin
          Require((Found.Attributes and $400) = 0);
          if (Found.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            CheckTree(Path + '\' + Found.Name);
        end;
      until not FindNext(Found);
    finally FindClose(Found); end;
  end;
end;

procedure CleanCompleted;
var Original, State: String;
begin
  Original := RecoveryFolder;
  RecoveryFolder := AppFolder + '\.cangoo-recovery.completed';
  try
    if not DirExists(RecoveryFolder) then Exit;
    CheckTree(RecoveryFolder);
    // 清理终态目录最后一步中断可仅留下空目录，安全重试即可。
    if RemoveDir(RecoveryFolder) then Exit;
    State := ReadState;
    Require((State = 'COMMITTED') or (State = 'RECOVERED'));
    if DirExists(RecoveryFolder + '\copies') and
      not DelTree(RecoveryFolder + '\copies', True, True, True) then Exit;
    DeleteFile(RecoveryFolder + '\restore.tmp');
    DeleteFile(RecoveryFolder + '\journal.tmp');
    DeleteFile(RecoveryFolder + '\journal');
    DeleteFile(RecoveryFolder + '\state.tmp');
    DeleteFile(RecoveryFolder + '\state');
    if not RemoveDir(RecoveryFolder) then WriteState(State);
  finally RecoveryFolder := Original; end;
end;

procedure CleanRecovery;
begin
  CleanCompleted;
  Require(not DirExists(AppFolder + '\.cangoo-recovery.completed'));
  if ReadState = 'PREPARING' then WriteState('RECOVERED');
  // 先原子移走已完成目录，再删备份；启动器不会看到清理到一半的事务。
  Require(ReplaceFile(RecoveryFolder, AppFolder + '\.cangoo-recovery.completed', 8));
  CleanCompleted;
end;

procedure RecoverPrevious;
var State, Name, Hash, Backup, Target, Temp: String;
  Lines: TArrayOfString; I, Separator: Integer;
begin
  if not DirExists(RecoveryFolder) then Exit;
  State := ReadState;
  if State = 'READY' then begin
    CheckProgramStopped;
    Require(LoadStringsFromFile(RecoveryFolder + '\journal', Lines));
    Require((GetArrayLength(Lines) > 0) and (GetArrayLength(Lines) <= 10000));
    Require(Lines[0] = RecoveryHeader + ' {#AppId}');
    // 完整校验先于任何恢复写入；恢复过程中始终保留原备份。
    for I := 1 to GetArrayLength(Lines) - 1 do begin
      Separator := Pos('|', Lines[I]);
      Require(Separator > 1);
      Hash := Copy(Lines[I], 1, Separator - 1);
      Name := Copy(Lines[I], Separator + 1, MaxInt);
      ValidateRelative(Name);
      CheckPath(AppFolder + '\' + Name);
      Backup := RecoveryFolder + '\copies\' + Name;
      CheckPath(Backup);
      Require(not DirExists(AppFolder + '\' + Name));
      if Hash <> '-' then Require((Length(Hash) = 64) and FileExists(Backup) and
        (CompareText(GetSHA256OfFile(Backup), Hash) = 0));
    end;
    for I := 1 to GetArrayLength(Lines) - 1 do begin
      Separator := Pos('|', Lines[I]);
      Hash := Copy(Lines[I], 1, Separator - 1);
      Name := Copy(Lines[I], Separator + 1, MaxInt);
      Target := AppFolder + '\' + Name;
      CheckPath(Target);
      if Hash = '-' then begin
        if FileExists(Target) then Require(DeleteFile(Target));
      end else if not FileExists(Target) or
        (CompareText(GetSHA256OfFile(Target), Hash) <> 0) then begin
        Temp := RecoveryFolder + '\restore.tmp';
        Require(ForceDirectories(ExtractFileDir(Target)));
        Require(FileCopy(RecoveryFolder + '\copies\' + Name, Temp, False));
        SyncFile(Temp);
        Require(CompareText(GetSHA256OfFile(Temp), Hash) = 0);
        Require(ReplaceFile(Temp, Target, 9));
        Require(CompareText(GetSHA256OfFile(Target), Hash) = 0);
      end;
    end;
    WriteState('RECOVERED');
    Log('CANGOO_PROGRAM_RECOVERED');
  end;
  // PREPARING 从未改旧程序；两个终态只清理，不再恢复。
  CleanRecovery;
  Require(not DirExists(RecoveryFolder));
  RecoveredInThisRun := True;
end;

procedure AddManifest(Path: String; Names: TStringList);
var Lines: TArrayOfString; I: Integer; Name: String;
begin
  Require(LoadStringsFromFile(Path, Lines));
  Require((GetArrayLength(Lines) > 0) and (GetArrayLength(Lines) <= 10000));
  Require(Lines[0] = FilesHeader);
  for I := 1 to GetArrayLength(Lines) - 1 do begin
    Name := Lines[I];
    ValidateRelative(Name);
    if Names.IndexOf(Name) < 0 then Names.Add(Name);
  end;
end;

procedure CleanInitialization;
var Path: String; Found: TFindRec;
begin
  Path := AppFolder + '\.cangoo-recovery.init';
  if not DirExists(Path) then Exit;
  CheckTree(Path);
  if FindFirst(Path + '\*', Found) then begin
    try
      repeat
        Require((Found.Name = '.') or (Found.Name = '..') or
          (Found.Name = 'state') or (Found.Name = 'state.tmp'));
      until not FindNext(Found);
    finally FindClose(Found); end;
  end;
  DeleteFile(Path + '\state.tmp');
  DeleteFile(Path + '\state');
  Require(RemoveDir(Path));
end;

procedure PrepareRecovery;
var Names: TStringList; Lines: TArrayOfString;
  I: Integer; Name, Source, Backup, Hash, FinalFolder: String; Found: TFindRec;
begin
  FinalFolder := RecoveryFolder;
  CleanInitialization;
  RecoveryFolder := AppFolder + '\.cangoo-recovery.init';
  CheckPath(RecoveryFolder);
  Require(ForceDirectories(RecoveryFolder));
  WriteState('PREPARING');
  Require(ReplaceFile(RecoveryFolder, FinalFolder, 8));
  RecoveryFolder := FinalFolder;
  OwnTransaction := True;
  // 标记生效后再次检查，缩小安装前检查与软件启动之间的竞态。
  CheckProgramStopped;
  Names := TStringList.Create;
  try
    Names.Sorted := True;
    AddManifest(ExpandConstant('{tmp}\incoming_manifest.txt'), Names);
    if FileExists(AppFolder + '\install_files.txt') then
      AddManifest(AppFolder + '\install_files.txt', Names);
    Names.Add('install_files.txt');
    if FindFirst(AppFolder + '\unins*.*', Found) then begin
      try
        repeat
          if (Found.Attributes and FILE_ATTRIBUTE_DIRECTORY) = 0 then begin
            ValidateRelative(Found.Name);
            if Names.IndexOf(Found.Name) < 0 then Names.Add(Found.Name);
          end;
        until not FindNext(Found);
      finally FindClose(Found); end;
    end;
    for I := 0 to 2 do begin
      if I = 0 then Name := 'unins000.exe'
      else if I = 1 then Name := 'unins000.dat' else Name := 'unins000.msg';
      if Names.IndexOf(Name) < 0 then Names.Add(Name);
    end;
    SetArrayLength(Lines, Names.Count + 1);
    Lines[0] := RecoveryHeader + ' {#AppId}';
    for I := 0 to Names.Count - 1 do begin
      Name := Names[I];
      Source := AppFolder + '\' + Name;
      Backup := RecoveryFolder + '\copies\' + Name;
      CheckPath(Source);
      Require(not DirExists(Source));
      Hash := '-';
      if FileExists(Source) then begin
        Require(ForceDirectories(ExtractFileDir(Backup)));
        Hash := GetSHA256OfFile(Source);
        Require(FileCopy(Source, Backup, True));
        SyncFile(Backup);
        Require(CompareText(GetSHA256OfFile(Backup), Hash) = 0);
        Require(CompareText(GetSHA256OfFile(Source), Hash) = 0);
      end;
      Lines[I + 1] := Hash + '|' + Name;
    end;
    Require(SaveStringsToUTF8File(RecoveryFolder + '\journal.tmp', Lines, False));
    SyncFile(RecoveryFolder + '\journal.tmp');
    Require(ReplaceFile(RecoveryFolder + '\journal.tmp', RecoveryFolder + '\journal', 9));
    WriteState('READY');
  finally Names.Free; end;
end;

procedure RemoveObsoleteProgramFiles;
var OldNames, NewNames: TStringList; I: Integer; Target: String;
begin
  if not FileExists(AppFolder + '\install_files.txt') then Exit;
  OldNames := TStringList.Create;
  NewNames := TStringList.Create;
  try
    OldNames.Sorted := True;
    NewNames.Sorted := True;
    AddManifest(AppFolder + '\install_files.txt', OldNames);
    AddManifest(ExpandConstant('{tmp}\incoming_manifest.txt'), NewNames);
    for I := 0 to OldNames.Count - 1 do
      if NewNames.IndexOf(OldNames[I]) < 0 then begin
        Target := AppFolder + '\' + OldNames[I];
        CheckPath(Target);
        Require(not DirExists(Target));
        if FileExists(Target) then Require(DeleteFile(Target));
      end;
  finally
    OldNames.Free;
    NewNames.Free;
  end;
end;

procedure CheckFreshTargets;
var Names: TStringList; I: Integer; Target: String;
begin
  Names := TStringList.Create;
  try
    AddManifest(ExpandConstant('{tmp}\incoming_manifest.txt'), Names);
    for I := 0 to Names.Count - 1 do begin
      Target := AppFolder + '\' + Names[I];
      CheckPath(Target);
      if FileExists(Target) or DirExists(Target) then
        RaiseException(CustomMessage('UnsafeFolder'));
    end;
  finally Names.Free; end;
end;

function DefaultProgramFolder(Param: String): String;
begin
  if IsAdminInstallMode then Result := ExpandConstant('{autopf}\{#MachineLeaf}')
  else begin
#ifdef CandidateDefaultDir
    Result := '{#CandidateDefaultDir}';
#else
    Result := ExpandConstant('{localappdata}\Programs\Cangoo');
#endif
  end;
end;

function ScopeKey: Integer;
begin
  if IsAdminInstallMode then Result := HKLM64 else Result := HKCU64;
end;

function ProgramFolder(Path: String): String;
begin
  Result := AddBackslash(RemoveBackslashUnlessRoot(Path)) + 'Cangoo';
end;

procedure ValidateProgramFolder(Path, Installed: String);
var Status: Integer;
begin
  Status := NativeFolder(Path, Installed, Ord(IsAdminInstallMode));
  if Status = 0 then Exit;
  if Status = 4 then RaiseException(CustomMessage('ChangeScope'));
  if Status = 3 then RaiseException(CustomMessage('UnsafeFolder'));
  if IsAdminInstallMode then RaiseException(CustomMessage('InvalidMachineFolder'));
  RaiseException(CustomMessage('InvalidInstallFolder'));
end;

procedure CheckLegacyMsi;
var Status: Integer;
begin
  Status := NativeLegacyMsi;
  if (Status = 1) or (Status = 2) then RaiseException(CustomMessage('LegacyMsi'));
  if Status <> 0 then RaiseException(CustomMessage('StateUnknown'));
end;

function ParseInstallVersion(Value: String; var Parts: TInstallVersion): Boolean;
var I, Part, Digits, Number: Integer; First: Char;
begin
  Result := False;
  if (Length(Value) < 5) or (Length(Value) > 17) then Exit;
  Value := Value + '.';
  Part := 0; Digits := 0; Number := 0; First := #0;
  for I := 1 to Length(Value) do begin
    if Value[I] = '.' then begin
      if (Part > 2) or (Digits = 0) or ((Digits > 1) and (First = '0')) then Exit;
      Parts[Part] := Number;
      Part := Part + 1; Digits := 0; Number := 0;
    end else begin
      if (Value[I] < '0') or (Value[I] > '9') then Exit;
      if Digits = 0 then First := Value[I];
      Digits := Digits + 1;
      if Digits > 5 then Exit;
      Number := Number * 10 + Ord(Value[I]) - Ord('0');
      if Number > 65535 then Exit;
    end;
  end;
  Result := Part = 3;
end;

procedure CheckInstalledVersion(Key: Integer);
var Installed, Incoming: TInstallVersion; I: Integer;
begin
  if not RegKeyExists(Key, UninstallKey) then Exit;
  if not RegQueryStringValue(Key, UninstallKey, 'DisplayVersion', InstalledVersion) or
    not ParseInstallVersion(InstalledVersion, Installed) or
    not ParseInstallVersion('{#AppVersion}', Incoming) then
    RaiseException(CustomMessage('InvalidInstallRegistration'));
  SetupOperation := 'Repair';
  for I := 0 to 2 do begin
    if Installed[I] > Incoming[I] then RaiseException(CustomMessage('DowngradeBlocked'));
    if Installed[I] < Incoming[I] then begin SetupOperation := 'Update'; Exit; end;
  end;
end;

function InitializeSetup: Boolean;
var I: Integer;
begin
  Result := False;
  SetupOperation := 'Install';
  FailureMessage := 'StateUnknown';
  for I := 1 to ParamCount do begin
    if CompareText(Copy(ParamStr(I), 1, 5), '/DIR=') = 0 then ExplicitDirectory := True;
    if (CompareText(ParamStr(I), '/VERYSILENT') = 0) or
      (CompareText(ParamStr(I), '/NOCANCEL') = 0) then begin
      SuppressibleMsgBox(CustomMessage('UnsupportedInstallMode'), mbError, MB_OK, IDOK);
      Exit;
    end;
  end;
  try
    CheckLegacyMsi;
    if RegKeyExists(ScopeKey, UninstallKey) then begin
      if not RegQueryStringValue(ScopeKey, UninstallKey, 'InstallLocation', MaintenanceFolder) or
        (MaintenanceFolder = '') then RaiseException(CustomMessage('InvalidInstallRegistration'));
      CheckInstalledVersion(ScopeKey);
      ValidateProgramFolder(MaintenanceFolder, MaintenanceFolder);
    end;
  except
    SuppressibleMsgBox(GetExceptionMessage, mbError, MB_OK, IDOK);
    Exit;
  end;
  Result := True;
end;

procedure ParentFolderChanged(Sender: TObject);
begin
  if Trim(ParentFolderEdit.Text) = '' then WizardForm.DirEdit.Text := ''
  else WizardForm.DirEdit.Text := ProgramFolder(ParentFolderEdit.Text);
end;

procedure BrowseParentFolder(Sender: TObject);
var Folder: String;
begin
  Folder := ParentFolderEdit.Text;
  if BrowseForFolder(CustomMessage('ParentFolder'), Folder, True) then
    ParentFolderEdit.Text := Folder;
end;

procedure MaintenanceUninstall(Sender: TObject);
var ExitCode: Integer;
begin
  UninstallButton.Enabled := False;
  WizardForm.NextButton.Enabled := False;
  if not Exec(AddBackslash(MaintenanceFolder) + 'unins000.exe', '', '', SW_SHOWNORMAL,
    ewWaitUntilTerminated, ExitCode) then begin
    Log('CANGOO_MAINTENANCE_UNINSTALL_START_FAILED: ' + IntToStr(ExitCode));
    MsgBox(CustomMessage('UninstallStartFailed'), mbError, MB_OK);
  end else begin
    Log('CANGOO_MAINTENANCE_UNINSTALL_EXIT: ' + IntToStr(ExitCode));
    Log('CANGOO_MAINTENANCE_UNINSTALL_REGISTRATION_REMAINS: ' +
      IntToStr(Ord(RegKeyExists(ScopeKey, UninstallKey))));
    Log('CANGOO_MAINTENANCE_UNINSTALL_PROGRAM_REMAINS: ' +
      IntToStr(Ord(FileExists(AddBackslash(MaintenanceFolder) + 'Cangoo.exe'))));
  end;
  // 子卸载无论取消还是完成，外层向导都结束。
  WizardForm.Close;
end;

procedure InitializeWizard;
begin
  if (MaintenanceFolder <> '') and not ExplicitDirectory then
    WizardForm.DirEdit.Text := MaintenanceFolder;
  WizardForm.Caption := '{#AppName} — ' + CustomMessage(SetupOperation);
  WizardForm.FilenameLabel.Visible := False;
  WizardForm.SelectDirBrowseLabel.Caption := '';
  if MaintenanceFolder <> '' then begin
    UninstallButton := TNewButton.Create(WizardForm);
    UninstallButton.Parent := WizardForm;
    UninstallButton.SetBounds(WizardForm.BackButton.Left, WizardForm.BackButton.Top,
      WizardForm.BackButton.Width, WizardForm.BackButton.Height);
    UninstallButton.Caption := CustomMessage('Uninstall');
    UninstallButton.OnClick := @MaintenanceUninstall;
    UninstallButton.Visible := False;
  end else begin
    if IsAdminInstallMode then begin
      WizardForm.SelectDirLabel.Caption := CustomMessage('MachineFolder');
      WizardForm.DirEdit.ReadOnly := True;
      WizardForm.DirBrowseButton.Visible := False;
    end else if ExplicitDirectory then
      WizardForm.SelectDirLabel.Caption := CustomMessage('ProgramFolderLabel')
    else begin
      WizardForm.SelectDirLabel.Caption := CustomMessage('ParentFolder');
      ParentFolderEdit := TNewEdit.Create(WizardForm);
      ParentFolderEdit.Parent := WizardForm.DirEdit.Parent;
      ParentFolderEdit.SetBounds(WizardForm.DirEdit.Left, WizardForm.DirEdit.Top,
        WizardForm.DirEdit.Width, WizardForm.DirEdit.Height);
      ParentFolderEdit.OnChange := @ParentFolderChanged;
      ParentFolderEdit.Text := ExtractFileDir(RemoveBackslashUnlessRoot(WizardForm.DirEdit.Text));
      ParentFolderEdit.TabOrder := WizardForm.DirEdit.TabOrder;
      WizardForm.DirEdit.Visible := False;
      WizardForm.DirBrowseButton.OnClick := @BrowseParentFolder;
    end;
    StartMenuChoice := TNewCheckBox.Create(WizardForm);
    StartMenuChoice.Parent := WizardForm.DirEdit.Parent;
    StartMenuChoice.SetBounds(WizardForm.DirEdit.Left,
      WizardForm.DirEdit.Top + WizardForm.DirEdit.Height + ScaleY(24),
      WizardForm.SelectDirLabel.Width, ScaleY(24));
    StartMenuChoice.Caption := CustomMessage('StartMenu');
    StartMenuChoice.Checked := False;
    DesktopChoice := TNewCheckBox.Create(WizardForm);
    DesktopChoice.Parent := StartMenuChoice.Parent;
    DesktopChoice.SetBounds(StartMenuChoice.Left, StartMenuChoice.Top + StartMenuChoice.Height + ScaleY(8),
      StartMenuChoice.Width, StartMenuChoice.Height);
    DesktopChoice.Caption := CustomMessage('Desktop');
    DesktopChoice.Checked := False;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  // 原生任务页已初始化后才同步首装选择；维护完全沿用原登记。
  if (PageID = wpSelectTasks) and (MaintenanceFolder = '') and not WizardSilent then begin
    WizardSelectTasks('!startmenu,!desktop');
    if StartMenuChoice.Checked then WizardSelectTasks('startmenu');
    if DesktopChoice.Checked then WizardSelectTasks('desktop');
  end;
  Result := (PageID = wpSelectTasks) or
    ((PageID = wpSelectDir) and (MaintenanceFolder <> '')) or
    ((PageID = wpReady) and (MaintenanceFolder = ''));
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  if SetupOperation = 'Update' then
    Result := FmtMessage(CustomMessage('UpdateVersion'), [InstalledVersion, '{#AppVersion}'])
  else Result := FmtMessage(CustomMessage('Version'), ['{#AppVersion}']);
  Result := Result + NewLine + NewLine + MemoDirInfo;
  if MaintenanceFolder <> '' then
    Result := Result + NewLine + NewLine + CustomMessage(SetupOperation + 'Action');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if UninstallButton <> nil then UninstallButton.Visible := CurPageID = wpReady;
  case CurPageID of
    wpSelectDir: begin
      WizardForm.PageNameLabel.Caption := CustomMessage('InstallReady');
      WizardForm.PageDescriptionLabel.Caption := FmtMessage(CustomMessage('Version'), ['{#AppVersion}']);
      WizardForm.NextButton.Caption := CustomMessage('Install');
    end;
    wpReady: begin
      WizardForm.PageNameLabel.Caption := CustomMessage(SetupOperation + 'Ready');
      WizardForm.PageDescriptionLabel.Caption := '';
      WizardForm.ReadyLabel.Visible := False;
      WizardForm.ReadyMemo.Top := WizardForm.ReadyLabel.Top;
      WizardForm.ReadyMemo.Height := WizardForm.ReadyPage.Height - WizardForm.ReadyMemo.Top;
      WizardForm.NextButton.Caption := CustomMessage(SetupOperation);
      WizardForm.CancelButton.Caption := CustomMessage('Close');
      WizardForm.BackButton.Visible := False;
    end;
    wpPreparing: begin
      WizardForm.PageNameLabel.Caption := CustomMessage('Preparing');
      WizardForm.PageDescriptionLabel.Caption := '';
    end;
    wpInstalling: begin
      WizardForm.PageNameLabel.Caption := CustomMessage(SetupOperation + 'Progress');
      WizardForm.PageDescriptionLabel.Caption := '';
      WizardForm.StatusLabel.Visible := False;
    end;
    wpFinished: begin
      if InstallCommitted and not IntegrityFailed then begin
        WizardForm.FinishedHeadingLabel.Caption := CustomMessage(SetupOperation + 'Complete');
        if not WizardForm.YesRadio.Visible then WizardForm.FinishedLabel.Caption := '';
      end else begin
        WizardForm.FinishedHeadingLabel.Caption := CustomMessage('NotComplete');
        WizardForm.FinishedLabel.Caption := CustomMessage('CommitFailed');
      end;
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var Target, Known: String;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and not WizardSilent then begin
    try
      Target := WizardForm.DirEdit.Text;
      Known := '';
      if DirExists(AddBackslash(Target) + RecoveryDirectory) then Known := Target;
      ValidateProgramFolder(Target, Known);
    except
      MsgBox(GetExceptionMessage, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CheckInstalledPayload;
var Lines: TArrayOfString; Names: TStringList; I, Separator, Index: Integer;
  Name, Hash: String;
begin
  Names := TStringList.Create;
  try
    AddManifest(ExpandConstant('{tmp}\incoming_manifest.txt'), Names);
    Names.Add('install_files.txt');
    Index := Names.IndexOf('_internal\payload_hashes.txt');
    Require(Index >= 0);
    Names.Delete(Index);
    Require(LoadStringsFromFile(ExpandConstant('{tmp}\incoming_hashes.txt'), Lines));
    Require(GetArrayLength(Lines) = Names.Count + 1);
    Require(Lines[0] = 'CANGOO-HASHES-1 {#AppId}');
    for I := 1 to GetArrayLength(Lines) - 1 do begin
      Separator := Pos('|', Lines[I]);
      Require(Separator = 65);
      Hash := Copy(Lines[I], 1, 64);
      Name := Copy(Lines[I], 66, MaxInt);
      ValidateRelative(Name);
      Index := Names.IndexOf(Name);
      Require(Index >= 0);
      Names.Delete(Index);
      CheckPath(AppFolder + '\' + Name);
      Require(FileExists(AppFolder + '\' + Name));
      Require(CompareText(GetSHA256OfFile(AppFolder + '\' + Name), Hash) = 0);
    end;
    Require(Names.Count = 0);
    CheckPath(AppFolder + '\_internal\payload_hashes.txt');
    Require(CompareText(GetSHA256OfFile(AppFolder + '\_internal\payload_hashes.txt'),
      GetSHA256OfFile(ExpandConstant('{tmp}\incoming_hashes.txt'))) = 0);
  finally Names.Free; end;
end;

procedure VerifyInstalledPayload;
begin
  FailureMessage := 'PayloadFailed';
  try CheckInstalledPayload;
  except
    IntegrityFailed := True;
    Log('CANGOO_PAYLOAD_VERIFICATION_FAILED: ' + GetExceptionMessage);
    SuppressibleMsgBox(CustomMessage('PayloadFailed'), mbError, MB_OK, IDOK);
    // 使用安装引擎的取消标志；回调自身的异常会被 Inno 捕获。
    WizardForm.CancelButton.OnClick(WizardForm.CancelButton);
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if IntegrityFailed then begin Cancel := True; Confirm := False; end
  else if not OwnTransaction or InstallCommitted or CommitFailed then Confirm := False
  else begin
    Confirm := False;
    Cancel := MsgBox(CustomMessage('Cancel' + SetupOperation), mbConfirmation, MB_YESNO) = IDYES;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Existing, Probe, ValidationKnown: String; CurrentKey, OtherKey, ProbeResult: Integer;
begin
  Result := '';
  FailureMessage := 'StateUnknown';
  try
    if InstallMutex = 0 then begin
      InstallMutex := AcquireMutex(0, False, 'Global\{#AppId}.Setup');
      if (InstallMutex = 0) or (LastWinError = 183) then begin
        if InstallMutex <> 0 then CloseFile(InstallMutex);
        InstallMutex := 0;
        RaiseException(CustomMessage('BusySetup'));
      end;
    end;
    AppFolder := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
    RecoveryFolder := AppFolder + '\' + RecoveryDirectory;
    CheckPath(AppFolder);
    if IsAdminInstallMode then begin CurrentKey := HKLM64; OtherKey := HKCU64; end
    else begin CurrentKey := HKCU64; OtherKey := HKLM64; end;
    if RegKeyExists(CurrentKey, UninstallKey) then begin
      if not RegQueryStringValue(CurrentKey, UninstallKey, 'InstallLocation', Existing) or
        (Existing = '') then RaiseException(CustomMessage('InvalidInstallRegistration'));
      CheckInstalledVersion(CurrentKey);
    end;
    if RegKeyExists(OtherKey, UninstallKey) or ((Existing <> '') and
      (CompareText(RemoveBackslashUnlessRoot(Existing), AppFolder) <> 0)) then
      RaiseException(CustomMessage('ChangeScope'));
    if IsAdminInstallMode then begin
      // 另一管理员凭据会改变 HKCU；用框架保留的原用户上下文只读固定卸载键。
      // 命令无用户输入，退出码区分不存在、已安装和无法检查。
      Probe := '-NoProfile -NonInteractive -Command "try {' +
        '$k=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey(''' + UninstallKey + ''');' +
        'if($null -eq $k){exit 0};$k.Dispose();exit 10}catch{exit 20}"';
      if not ExecAsOriginalUser(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
        Probe, '', SW_HIDE, ewWaitUntilTerminated, ProbeResult) then
        RaiseException(CustomMessage('ScopeCheckFailed'));
      if ProbeResult = 10 then RaiseException(CustomMessage('ChangeScope'));
      if ProbeResult <> 0 then RaiseException(CustomMessage('ScopeCheckFailed'));
    end;
    CheckLegacyMsi;
    ValidationKnown := Existing;
    if (ValidationKnown = '') and DirExists(RecoveryFolder) then ValidationKnown := AppFolder;
    ValidateProgramFolder(AppFolder, ValidationKnown);
    CheckProgramStopped;
    FailureMessage := 'RecoveryFailed';
    CleanCompleted;
    if DirExists(RecoveryFolder) then begin
      WizardForm.PageNameLabel.Caption := CustomMessage('Recovering');
      RecoverPrevious;
      WizardForm.PageNameLabel.Caption := CustomMessage('Preparing');
    end;
    OwnTransaction := False;
    FailureMessage := 'StateUnknown';
    CleanInitialization;
    ExtractTemporaryFile('incoming_manifest.txt');
    ExtractTemporaryFile('incoming_hashes.txt');
    if FileExists(AppFolder + '\portable.mode') then RaiseException(CustomMessage('UnsafeFolder'));
    if (Existing = '') and not RecoveredInThisRun and
       not FileExists(AppFolder + '\install_files.txt') then CheckFreshTargets;
    FailureMessage := 'BackupFailed';
    PrepareRecovery;
    FailureMessage := 'OperationStopped';
    RemoveObsoleteProgramFiles;
  except
    Result := GetExceptionMessage;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and OwnTransaction and not IntegrityFailed then begin
    FailureMessage := 'CommitFailed';
    try
      WriteState('COMMITTED');
      InstallCommitted := True;
    except
      // 引擎已结束内建回滚；保留未提交事务，不能恢复旧文件配上新登记。
      CommitFailed := True;
      Log('CANGOO_COMMIT_FAILED: ' + GetExceptionMessage);
    end;
    if InstallCommitted then begin
      try CleanRecovery;
      except Log('CANGOO_COMMITTED_CLEANUP_PENDING'); end;
    end;
  end;
end;

function GetCustomSetupExitCode: Integer;
begin
  Result := 0;
  if OwnTransaction and not InstallCommitted then Result := 1;
end;

procedure DeinitializeSetup;
var RestoreNeeded: Boolean;
begin
  if OwnTransaction and not InstallCommitted and not CommitFailed then begin
    FailureMessage := 'RecoveryFailed';
    try
      RestoreNeeded := (ReadState = 'READY') and (InstalledVersion <> '');
      RecoverPrevious;
      if RestoreNeeded then
        SuppressibleMsgBox(CustomMessage('ProgramRecovered'), mbInformation, MB_OK, IDOK);
    except SuppressibleMsgBox(CustomMessage('RecoveryFailed'), mbError, MB_OK, IDOK); end;
  end;
  if InstallMutex <> 0 then CloseFile(InstallMutex);
end;

function InitializeUninstall: Boolean;
begin
  FailureMessage := 'StateUnknown';
  UninstallMutex := AcquireMutex(0, False, 'Global\{#AppId}.Setup');
  Result := (UninstallMutex <> 0) and (LastWinError <> 183);
  if not Result then begin
    SuppressibleMsgBox(CustomMessage('BusySetup'), mbError, MB_OK, IDOK);
    Exit;
  end;
  AppFolder := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  RecoveryFolder := AppFolder + '\' + RecoveryDirectory;
  try
    if IsAdminInstallMode then
      Require(CompareText(AppFolder, ExpandConstant('{autopf}\{#MachineLeaf}')) = 0);
#ifdef CandidateRoot
    if not IsAdminInstallMode then
      Require(CompareText(Copy(AppFolder, 1, Length('{#CandidateRoot}\')), '{#CandidateRoot}\') = 0);
#endif
    CheckTree(AppFolder);
    Require(FileCopy(AppFolder + '\_internal\cangoo_inno_support.dll',
      ExpandConstant('{tmp}\cangoo_inno_support.dll'), True));
    Require(CompareText(GetSHA256OfFile(ExpandConstant('{tmp}\cangoo_inno_support.dll')), '{#SupportHash}') = 0);
    CheckProgramStopped;
    if DirExists(RecoveryFolder) then begin
      Result := (ReadState = 'COMMITTED') or (ReadState = 'RECOVERED');
      if Result then CleanRecovery else SuppressibleMsgBox(CustomMessage('PendingUpdate'), mbError, MB_OK, IDOK);
    end;
    if Result then Result := CleanupChooseData;
  except
    SuppressibleMsgBox(GetExceptionMessage, mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then CheckProgramStopped;
  if (CurUninstallStep = usPostUninstall) and CleanupConfirmed and not UninstallSilent then begin
    // usPost 本身不表示成功；根目录、登记及引擎无需重启必须同时确认。
    if CleanupNoRestart and not DirExists(AppFolder) and not FileExists(AppFolder) and
      not RegKeyExists(ScopeKey, UninstallKey) then begin
      CleanupStatus := NativeCleanup(CleanupDeletedCount, CleanupDeletedMask, CleanupRetainedMask, CleanupError) + 1;
      CleanupReportFailure;
    end else if not CleanupNoRestart then
      MsgBox(CustomMessage('CleanupRestartResult'), mbInformation, MB_OK)
    else MsgBox(CustomMessage('CleanupRetainedResult'), mbInformation, MB_OK);
  end;
end;

procedure DeinitializeUninstall;
begin
  UnloadDLL(ExpandConstant('{tmp}\cangoo_inno_support.dll'));
  if UninstallMutex <> 0 then CloseFile(UninstallMutex);
end;
