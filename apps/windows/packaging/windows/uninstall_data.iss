// 资料清理由共用 C++ 实现固定身份、普通令牌和六个文件；脚本只负责当次选择。
const
  CleanupRetained = 0;
  CleanupComplete = 1;
  CleanupIdentityUnknown = 2;
  CleanupFailed = 3;
  CleanupPartial = 4;
var
  CleanupConfirmed, CleanupNoRestart: Boolean;
  CleanupStatus: Integer;
  CleanupDeletedCount, CleanupDeletedMask, CleanupRetainedMask, CleanupError: LongWord;
  CleanupChoice: TNewCheckBox;
  CleanupContinue: TNewButton;
  CleanupWarning: TNewStaticText;

function NativeFolder(Path, Installed: String; Machine: Integer): Integer;
  external 'CangooInnoValidateFolder@files:cangoo_inno_support.dll stdcall setuponly';
function NativeLegacyMsi: Integer;
  external 'CangooInnoLegacyMsiState@files:cangoo_inno_support.dll stdcall setuponly';
function CleanupCurrentIdentity: Boolean;
  external 'CangooInnoCleanupIdentity@{tmp}\cangoo_inno_support.dll stdcall delayload uninstallonly';
function NativeCleanup(var Count, Deleted, Retained, Error: LongWord): Integer;
  external 'CangooInnoCleanup@{tmp}\cangoo_inno_support.dll stdcall delayload uninstallonly';

function UninstallNeedRestart: Boolean;
begin
  // 7.1.0 只在内建卸载步骤未要求重启时调用，未调用就保留资料。
  CleanupNoRestart := True;
  Result := False;
end;

function CleanupFileLabels(Mask: Integer): String;
var I: Integer; LabelText: String;
begin
  Result := '';
  for I := 0 to 5 do
    if (Mask and (1 shl I)) <> 0 then begin
      case I of
        0: LabelText := CustomMessage('CleanupVault');
        1: LabelText := 'pdm.db-wal';
        2: LabelText := 'pdm.db-shm';
        3: LabelText := 'pdm.db-journal';
        4: LabelText := CustomMessage('CleanupSettings');
        5: LabelText := CustomMessage('CleanupSecurity');
      end;
      if Result <> '' then Result := Result + ', ';
      Result := Result + LabelText;
    end;
end;

procedure CleanupReportFailure;
var Message: String;
begin
  if UninstallSilent or (CleanupStatus < CleanupIdentityUnknown) then Exit;
  if CleanupStatus = CleanupPartial then
    Message := FmtMessage(CustomMessage('CleanupPartialResult'), [
      CleanupFileLabels(CleanupDeletedMask),
      CleanupFileLabels(CleanupRetainedMask)])
  else if CleanupStatus = CleanupIdentityUnknown then
    Message := CustomMessage('CleanupIdentityResult')
  else Message := CustomMessage('CleanupFailedResult');
  MsgBox(Message, mbError, MB_OK);
end;

procedure CleanupChoiceChanged(Sender: TObject);
begin
  CleanupWarning.Visible := CleanupChoice.Checked;
end;

function CleanupChooseData: Boolean;
var Form: TSetupForm; Heading, Summary, Detail, Warning: TNewStaticText;
  CancelButton: TNewButton; IdentityKnown: Boolean; ButtonTop, ButtonWidth: Integer;
begin
  Result := True; CleanupConfirmed := False; CleanupStatus := CleanupRetained;
  if UninstallSilent then Exit;
  IdentityKnown := CleanupCurrentIdentity;
  // Inno 7.1 在构造时缩放窗体；传入设计尺寸，避免重复缩放。
  Form := CreateCustomForm(540, 300, True, True);
  try
    Form.Caption := '{#AppName} — ' + CustomMessage('Uninstall');
    Heading := TNewStaticText.Create(Form);
    Heading.Parent := Form;
    Heading.SetBounds(ScaleX(24), ScaleY(20), Form.ClientWidth - ScaleX(48), ScaleY(26));
    Heading.AutoSize := False;
    Heading.Font.Style := [fsBold];
    Heading.Caption := CustomMessage('CleanupHeading');
    Heading.AdjustHeight;
    Summary := TNewStaticText.Create(Form);
    Summary.Parent := Form;
    Summary.SetBounds(Heading.Left, Heading.Top + Heading.Height + ScaleY(16), Heading.Width, 0);
    Summary.AutoSize := False; Summary.WordWrap := True;
    Summary.Caption := CustomMessage('CleanupSummary');
    Summary.AdjustHeight;
    CleanupChoice := TNewCheckBox.Create(Form);
    CleanupChoice.Parent := Form;
    CleanupChoice.SetBounds(Heading.Left, Summary.Top + Summary.Height + ScaleY(20), Heading.Width, ScaleY(26));
    CleanupChoice.Caption := CustomMessage('CleanupOption');
    CleanupChoice.Checked := False;
    CleanupChoice.Enabled := IdentityKnown;
    CleanupChoice.OnClick := @CleanupChoiceChanged;
    Detail := TNewStaticText.Create(Form);
    Detail.Parent := Form;
    Detail.SetBounds(Heading.Left, CleanupChoice.Top + CleanupChoice.Height + ScaleY(8), Heading.Width, 0);
    Detail.AutoSize := False; Detail.WordWrap := True;
    Detail.Caption := CustomMessage('CleanupDetail');
    Detail.AdjustHeight;
    CleanupWarning := TNewStaticText.Create(Form);
    CleanupWarning.Parent := Form;
    CleanupWarning.SetBounds(Heading.Left, Detail.Top + Detail.Height + ScaleY(16), Heading.Width, 0);
    CleanupWarning.AutoSize := False; CleanupWarning.WordWrap := True;
    CleanupWarning.Caption := CustomMessage('CleanupWarning');
    CleanupWarning.AdjustHeight;
    ButtonTop := CleanupWarning.Top + CleanupWarning.Height + ScaleY(24);
    Warning := TNewStaticText.Create(Form);
    Warning.Parent := Form;
    Warning.SetBounds(Heading.Left, ButtonTop, Heading.Width, 0);
    Warning.AutoSize := False; Warning.WordWrap := True;
    if not IdentityKnown then begin
      Warning.Caption := CustomMessage('CleanupIdentityUnavailable');
      Warning.AdjustHeight;
      ButtonTop := Warning.Top + Warning.Height + ScaleY(24);
    end;
    ButtonWidth := Form.CalculateButtonWidth([CustomMessage('CleanupContinue'), SetupMessage(msgButtonCancel)]);
    Form.ClientHeight := ButtonTop + ScaleY(54);
    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.SetBounds(Form.ClientWidth - ScaleX(24) - ButtonWidth, ButtonTop, ButtonWidth, ScaleY(30));
    CancelButton.Caption := SetupMessage(msgButtonCancel);
    CancelButton.ModalResult := mrCancel; CancelButton.Cancel := True;
    CleanupContinue := TNewButton.Create(Form);
    CleanupContinue.Parent := Form;
    CleanupContinue.SetBounds(CancelButton.Left - ScaleX(8) - ButtonWidth, ButtonTop, ButtonWidth, ScaleY(30));
    CleanupContinue.Caption := CustomMessage('CleanupContinue');
    CleanupContinue.ModalResult := mrOk; CleanupContinue.Default := True;
    CleanupChoiceChanged(nil);
    Form.ActiveControl := CleanupContinue;
    Form.FlipAndCenterIfNeeded(True, nil, False);
    Result := Form.ShowModal = mrOk;
    CleanupConfirmed := Result and CleanupChoice.Checked and IdentityKnown;
  finally
    CleanupChoice := nil; CleanupContinue := nil; CleanupWarning := nil;
    Form.Free;
  end;
end;
