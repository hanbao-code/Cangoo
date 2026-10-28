; 仅从干净的目录式程序构建；用户数据不作为安装文件。
#ifndef AppId
  #define AppId "hanbao-code.Cangoo"
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef ManifestFile
  #error ManifestFile is required
#endif

#ifndef AppName
  #define AppName "Cangoo"
#endif
#ifndef ShortcutName
  #define ShortcutName "Cangoo"
#endif
#ifndef MachineLeaf
  #define MachineLeaf "Cangoo"
#endif
#ifndef SupportDll
  #error SupportDll is required
#endif
#ifndef SupportHash
  #error SupportHash is required
#endif
#ifndef PayloadHashesFile
  #error PayloadHashesFile is required
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=hanbao-code
AppPublisherURL=https://github.com/hanbao-code/Cangoo
DefaultDirName={code:DefaultProgramFolder}
AppendDefaultDirName=no
DisableDirPage=no
AlwaysShowDirOnReadyPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousPrivileges=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
ShowLanguageDialog=auto
DirExistsWarning=no
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
SetupArchitecture=x64
MinVersion=10.0.17763
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
#ifdef OutputDir
OutputDir={#OutputDir}
#endif
OutputBaseFilename=cangoo-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\resources\icons\cangoo\app.ico
UninstallDisplayIcon={app}\Cangoo.exe
SetupMutex=Global\{#AppId}.SetupUI
CloseApplications=no
RestartApplications=no
AllowCancelDuringInstall=yes
VersionInfoVersion={#AppVersion}.0

[Languages]
Name: "zh"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
zh.PrivilegesRequiredOverrideCurrentUserRecommended=仅为我安装(&M)（推荐）
en.PrivilegesRequiredOverrideCurrentUserRecommended=Install for &me only (recommended)
zh.PrivilegesRequiredOverrideAllUsers=为所有用户安装(&A)（需要管理员权限）
en.PrivilegesRequiredOverrideAllUsers=Install for &all users (requires administrator privileges)
zh.WizardSelectDir=安装位置
en.WizardSelectDir=Installation folder
zh.SelectDirDesc=
en.SelectDirDesc=
zh.SelectDirBrowseLabel=
en.SelectDirBrowseLabel=
zh.WizardSelectTasks=快捷方式
en.WizardSelectTasks=Shortcuts
zh.SelectTasksDesc=
en.SelectTasksDesc=
zh.SelectTasksLabel2=选择需要创建的快捷方式：
en.SelectTasksLabel2=Choose the shortcuts to create:
zh.ReadyMemoDir=程序目录：
en.ReadyMemoDir=Program folder:
zh.ReadyMemoTasks=快捷方式：
en.ReadyMemoTasks=Shortcuts:
zh.ExitSetupMessage=取消本次操作并恢复原程序？
en.ExitSetupMessage=Cancel this operation and restore the previous program?
zh.UninstalledAll=小仓程序已卸载。
en.UninstalledAll=The Cangoo program has been uninstalled.

zh.ConfirmUninstall=卸载小仓，并按上一步的选择保留或清除资料？
en.ConfirmUninstall=Uninstall Cangoo and keep or clear data as selected in the previous step?

[CustomMessages]
zh.StartMenu=创建开始菜单快捷方式
en.StartMenu=Create a Start menu shortcut
zh.Desktop=创建桌面快捷方式
en.Desktop=Create a desktop shortcut
zh.CloseApp=暂时无法修改小仓程序文件。请从托盘退出小仓后重试。
en.CloseApp=Cangoo program files cannot be changed right now. Exit Cangoo from the system tray and try again.
zh.RecoveryFailed=未能恢复原程序，请保留安装文件夹并获取帮助。
en.RecoveryFailed=The previous program could not be restored. Keep the installation folder and get help.
zh.UnsafeFolder=此位置已有其他文件，请选择其他文件夹。
en.UnsafeFolder=This location contains other files. Choose another folder.
zh.ChangeScope=已安装的小仓位于另一位置或安装范围，请先卸载原程序并保留资料。
en.ChangeScope=Cangoo is installed in another location or scope. Uninstall the existing program and keep your data first.
zh.ScopeCheckFailed=无法确认当前安装状态，本次操作未开始。请在自己的 Windows 账号中运行安装包。
en.ScopeCheckFailed=The installation state could not be verified. No changes were started. Run Setup from your own Windows account.
zh.PendingUpdate=上次安装尚未完成，请先运行安装包恢复，再卸载。
en.PendingUpdate=The previous installation is incomplete. Run Setup to recover before uninstalling.
zh.CleanupHeading=资料处理
en.CleanupHeading=Your data
zh.CleanupSummary=默认保留资料。
en.CleanupSummary=Data is kept by default.
zh.CleanupOption=清除当前账号的默认密码库、设置和安全记录
en.CleanupOption=Clear this account’s default vault, settings and security records
zh.CleanupDetail=其他密码库、所有备份及其他 Windows 账号的资料保留。
en.CleanupDetail=Other vaults, all backups and other Windows accounts’ data will be kept.
zh.CleanupIdentityUnavailable=无法确认资料所属账号，本次只能保留资料。
en.CleanupIdentityUnavailable=The account that owns the data could not be confirmed. Data must be kept.
zh.CleanupVault=默认库 pdm.db
en.CleanupVault=Default vault (pdm.db)
zh.CleanupSettings=设置
en.CleanupSettings=Settings
zh.CleanupSecurity=安全记录
en.CleanupSecurity=Security records
zh.CleanupIdentityResult=无法确认资料所属账号，资料未清除。
en.CleanupIdentityResult=The account that owns the data could not be confirmed. No data was cleared.
zh.CleanupFailedResult=资料未清除。其他密码库和所有备份未受影响。
en.CleanupFailedResult=No data was cleared. Other vaults and all backups are unaffected.
zh.CleanupPartialResult=资料仅部分清除。%n%n已清除：%1%n保留：%2%n%n已清除的资料无法撤销。其他密码库和所有备份未受影响。
en.CleanupPartialResult=Only part of the data was cleared.%n%nCleared: %1%nKept: %2%n%nCleared data cannot be restored by Cangoo. Other vaults and all backups are unaffected.

zh.LegacyMsi=请先卸载旧版小仓，保留资料，不勾选清除资料。卸载完成后，再打开此安装包。
en.LegacyMsi=Uninstall the previous Cangoo installation first, leaving data cleanup unchecked. Then reopen this installer.
zh.InvalidInstallFolder=此位置无法用于安装，请选择其他本地文件夹。
en.InvalidInstallFolder=This location cannot be used for installation. Choose another local folder.
zh.ParentFolder=存放 Cangoo 文件夹的位置：
en.ParentFolder=Location for the Cangoo folder:
zh.CleanupRetainedResult=程序尚未完全卸载，资料已保留。
en.CleanupRetainedResult=The program has not been fully uninstalled. Your data was kept.

zh.UnsupportedInstallMode=不支持 /VERYSILENT 或 /NOCANCEL，请使用普通安装或 /SILENT。
en.UnsupportedInstallMode=/VERYSILENT and /NOCANCEL are not supported. Use the normal wizard or /SILENT.
zh.PayloadFailed=程序文件校验失败，本次操作将取消。
en.PayloadFailed=Program file verification failed. This operation will be cancelled.

zh.InvalidInstallRegistration=无法确认现有安装信息，本次操作未开始。请保留安装文件夹并获取帮助。
en.InvalidInstallRegistration=The existing installation information could not be verified. No changes were started. Keep the installation folder and get help.
zh.DowngradeBlocked=此安装包比已安装版本旧，请使用相同或更新版本的安装包。
en.DowngradeBlocked=This installer is older than the installed version. Use the same or a newer version.

zh.UninstallStartFailed=未能启动卸载程序，尚未卸载。
en.UninstallStartFailed=The uninstaller could not start. Nothing has been uninstalled.

zh.Install=安装
en.Install=Install

zh.Repair=修复
en.Repair=Repair

zh.Update=更新
en.Update=Update

zh.Uninstall=卸载
en.Uninstall=Uninstall

zh.Exit=退出
en.Exit=Exit



zh.MachineFolder=所有用户安装使用下方受保护的系统程序目录。
en.MachineFolder=All-users installation uses the protected system programs folder below.

zh.InstallReady=安装小仓
en.InstallReady=Install Cangoo

zh.RepairReady=维护小仓
en.RepairReady=Maintain Cangoo

zh.UpdateReady=更新小仓
en.UpdateReady=Update Cangoo



zh.InstallProgress=正在安装
en.InstallProgress=Installing

zh.RepairProgress=正在修复
en.RepairProgress=Repairing

zh.UpdateProgress=正在更新
en.UpdateProgress=Updating


zh.InstallComplete=安装完成
en.InstallComplete=Installation complete

zh.RepairComplete=修复完成
en.RepairComplete=Repair complete

zh.UpdateComplete=更新完成
en.UpdateComplete=Update complete


zh.RepairAction=重新安装程序文件，密码库和设置保留。
en.RepairAction=Reinstall program files. Your vaults and settings will be kept.
zh.UpdateAction=更新程序，密码库和设置保留。
en.UpdateAction=Update the program. Your vaults and settings will be kept.
zh.CleanupContinue=继续
en.CleanupContinue=Continue
zh.CleanupWarning=将清除默认库 pdm.db、设置（含最近库路径）及验证失败／锁定记录，无法撤销。
en.CleanupWarning=The default vault (pdm.db), settings (including recent vault paths) and failed verification / lockout records will be permanently cleared.
zh.CleanupRestartResult=需要重启，资料暂未清除。
en.CleanupRestartResult=A restart is required. Your data has not been cleared.
zh.BusySetup=另一个安装或卸载正在进行，请完成后重试。
en.BusySetup=Another installation or uninstallation is running. Finish it and try again.
zh.StateUnknown=无法确认当前安装状态，本次操作未开始。
en.StateUnknown=The current installation state could not be verified. No changes were started.
zh.InvalidMachineFolder=无法使用系统程序目录，请联系此电脑的管理员。
en.InvalidMachineFolder=The system programs folder cannot be used. Contact this computer’s administrator.
zh.BackupFailed=未能保存原程序，本次操作已停止。
en.BackupFailed=The previous program could not be saved. This operation has stopped.
zh.OperationStopped=本次操作已停止。请保留安装文件夹并获取帮助。
en.OperationStopped=This operation has stopped. Keep the installation folder and get help.
zh.CommitFailed=安装尚未完成。请保留安装文件夹，重新运行本安装包恢复。
en.CommitFailed=Installation is incomplete. Keep the installation folder and run this installer again to recover.
zh.NotComplete=操作未完成
en.NotComplete=Operation incomplete
zh.ProgramRecovered=原程序已恢复。
en.ProgramRecovered=The previous program has been restored.
zh.Preparing=正在准备
en.Preparing=Preparing
zh.Recovering=正在恢复原程序
en.Recovering=Restoring the previous program
zh.Version=版本：%1
en.Version=Version: %1
zh.UpdateVersion=版本：%1 → %2
en.UpdateVersion=Version: %1 → %2
zh.ProgramFolderLabel=程序位置：
en.ProgramFolderLabel=Program location:
zh.Close=关闭
en.Close=Close
zh.CancelInstall=取消本次安装？已写入的程序文件将移除。
en.CancelInstall=Cancel this installation? Program files already installed will be removed.
zh.CancelRepair=取消本次修复并恢复原程序？
en.CancelRepair=Cancel this repair and restore the previous program?
zh.CancelUpdate=取消本次更新并恢复原程序？
en.CancelUpdate=Cancel this update and restore the previous program?

[Tasks]
Name: "startmenu"; Description: "{cm:StartMenu}"; Flags: unchecked
Name: "desktop"; Description: "{cm:Desktop}"; Flags: unchecked

[Files]
Source: "{#SupportDll}"; DestName: "cangoo_inno_support.dll"; Flags: dontcopy
Source: "{#PayloadHashesFile}"; DestName: "incoming_hashes.txt"; Flags: dontcopy
Source: "{#ManifestFile}"; DestName: "incoming_manifest.txt"; Flags: dontcopy
Source: "{#PayloadDir}\Cangoo.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\cangoo_strength_worker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ManifestFile}"; DestDir: "{app}"; DestName: "install_files.txt"; Flags: ignoreversion; AfterInstall: VerifyInstalledPayload

[Icons]
Name: "{autoprograms}\{#ShortcutName}"; Filename: "{app}\Cangoo.exe"; Tasks: startmenu
Name: "{autodesktop}\{#ShortcutName}"; Filename: "{app}\Cangoo.exe"; Tasks: desktop

[UninstallDelete]
Type: dirifempty; Name: "{app}"

[Code]
#include "uninstall_data.iss"
#include "recovery.iss"
