# Cangoo for Android 1.0.0 — User Guide

[简体中文](user_guide_zh.md) · [Project home](../../README.md) · [Release notes](../../release_notes.md) · [Third-party sources and licenses](../../third_party/android/README.md)



## First use and your first vault

1. On first launch, read the license notice, choose to continue and follow the introduction to My vaults.
2. Choose New vault. Enter a name and master password, enter the master password again to confirm it, then choose Create vault. You can now save your information.
3. On later visits, select this vault and enter its own master password. Separate vaults can keep personal and work information apart.

Master passwords are case-sensitive, including leading and trailing spaces. With an empty master password, anyone able to use Cangoo can open this vault, and quick unlock is unavailable. Set a master password that only you know.
Vaults are stored on this phone. Cangoo has no recovery function for master or backup passwords, so keep each password safe. Export encrypted backups regularly and store their passwords separately from the files. Uninstalling Cangoo, clearing app data or resetting the phone deletes vaults stored inside the app.

## Add, edit and delete items

1. Tap + on Home or All, then choose Add password or Add note.
2. For a password, enter its name, account and password, with optional notes. For a note, enter a title and body. Choose Save password or Save note to store the item.
3. Open it again to check the saved content. Choose Edit to make changes and save them. To delete an item, use the delete action in its edit page and confirm. Deletion cannot be directly undone, so back up important information first.

Clearing the ordinary password field and saving makes the password empty; it does not keep the old password. Change an account password with the website or app first, then update Cangoo. Cangoo does not change the external account for you.
If saving fails, correct the input or retry as instructed. If the record has changed, review its latest content before deciding whether to discard your draft.

## Find, favorite and sort items

Home shows favorites and recently opened items. Tap the star in an item’s details to add or remove it from favorites.
All lets you browse passwords and notes and filter favorites. Passwords can also be filtered for weak or repeated values. Choose Recently updated or Name order to change the list order.
Tap Search and enter text from a name, account or note body. Search does not include passwords, authenticator setup keys or recovery codes. If an item is missing, check the current vault, then clear the search or filters.

## One-time codes and recovery codes

One-time codes: enable One-time code while adding or editing a password record. Enter the authenticator setup key supplied by the service, save, then view or copy the current code from the details. Do not enter the current displayed code as the setup key. If a service rejects codes, check its configuration and the phone’s time.
Recovery codes: enter the service’s codes one per line and save. Reveal or copy individual codes from the details. Choose Mark used after using one, or Undo used if marked by mistake. These marks only help you remember which codes you have used; they do not change their usage status with the service.
Existing keys and recovery codes are kept by default. Choose Replace to change them; an empty replacement input still keeps the existing content. Choose Remove explicitly to delete them when you save. Replacing a whole set of recovery codes resets local used marks.

These recovery codes belong to the corresponding website or app. They cannot recover your Cangoo master password.

## Generate a password or check its strength

1. Open Tools → Generate password. Choose a length and at least one character category, then generate.
2. Reveal or copy the result, or choose Use in new record to place it in a password form. Complete the details and save. Generate password in a form also fills the field directly. Parameters changes and remembers the generator settings without changing the password already filled in.
3. To check a single password, open Tools → Analyze password strength, enter it and analyze. Read the result and advice, then clear the input or go back.

Generating or copying is not saving and does not change an external account. Tool results clear after one minute by default. Adjust or disable this in Settings. Viewing or copying does not extend the time; setting changes apply to the next generation. Clearing the result does not clear a password already placed in a form or saved.
Strength analysis happens on this device. Ratings and estimated cracking times are estimates. Use a different password for each account.

## Check passwords in the vault

Open Tools → Password checks to see weak, repeated and pending passwords in the current vault. Open a flagged record to inspect it. If needed, change the password with the service, then edit the Cangoo record.
Saving finishes first and strength ratings update afterwards. Items that have not been checked or whose checks failed do not yet have usable results; continue or retry as prompted. After cancelling checks, choose Continue checks to resume. Saving another record does not resume them for you.
Records with no password are excluded. Results help you spot issues; they do not guarantee account security.

## Create an encrypted backup

1. Unlock the vault to back up. Open Settings → Backup and restore, or the same entry under Tools, then choose Create backup.
2. Check the current vault. Choose all records, passwords only or notes only, then set a separate password for this backup and enter it again to confirm. The backup password cannot be empty.
3. Choose Create backup and select a local destination in the system file picker. After the saved confirmation, check the file. Create another vault with no data and try restoring the backup there to check that both the file and password work.

Backups contain the selected records, but not the master password or app settings. Fingerprint or face quick unlock is not transferred either. Opening this backup requires the password set when it was exported. Keep that password separately from the file. Use encrypted backups or Device transfer to move data to another device or between Windows and Android; do not exchange native vault files.
A failed or cancelled export may leave an empty or incomplete file. Check it in the file manager as instructed. The local recent-backup entry only records an operation; it does not guarantee the file still exists or can be restored.

## Restore a backup and compare changes

Choose the vault that will receive the data. If it already contains information, back it up first. You can also try a new empty vault.
1. Unlock that vault and choose Restore from backup in Backup and restore. Select a local backup file, enter its backup password and choose Preview contents. A large backup can take time to open; animated dots mean processing continues.
2. Check the destination vault and the passwords and notes to import. New items will be added and identical content is skipped automatically. Open a record to compare both sides. To view a hidden value such as a password, use its Show both action. Read full comparison opens long text for reading in sections.
3. For records whose contents differ, choose Keep current or Replace current. A note from the backup can also be added while keeping existing notes. If several notes have similar titles, choose the current note to compare, then explicitly decide whether to replace it. Changing the comparison alone does not change your previous decision.
4. Filter by action status or changed field. Use Selection at the bottom to select this page or Select filtered conflicts across pages, then choose Batch actions, select an action and confirm. Changing filters does not clear previous selections; check selected items outside the current list too. Notes needing individual review keep their previous decisions. Open their details to handle them separately.
5. When Pending reaches zero, review the added, replaced and skipped counts. Choose Confirm restore and give the final confirmation. Only then does Cangoo write the chosen records to the vault. Check the saved records afterwards. Cancelling the preview discards these choices.

Replacement changes the whole record, not just one field. Other current records absent from the backup are not deleted. If this record in the backup has no recovery codes, replacement clears current codes and their used marks; read the warning first. An old backup also restores used marks from that time, so check actual code usage again. Keep current avoids replacement.
Taps and scrolling restart the idle timer while comparing. If you stop interacting, the usual auto-lock setting applies; there is no extra preview deadline. Start a new preview after closing, cancelling, locking or switching vaults. If the password is wrong, the file is damaged or the data has changed, check and retry as prompted.
If the file picker does not show a file, browse to its saved folder through the phone’s internal storage. If the vault locks while choosing a file, unlock the original destination and re-enter the backup password as prompted to continue. Restart after switching vaults.

## Send or receive from a nearby device

1. Unlock the intended vault on each device and open Settings → Device transfer. Choose Send data on one and Receive data on the other, using the same connection method. The vault names do not need to match.
2. For LAN, connect both devices to the same Wi-Fi or to a hotspot turned on manually on one device. If a Windows device needs permission, choose Allow local device connections there and confirm its system prompt. For Bluetooth Classic, pair in system settings first, keep Bluetooth on and allow connection permissions when prompted.
3. The receiver chooses Wait to receive (Wait for sender on Windows) first. Once the receiver is waiting, the sender chooses Find receiving devices (Find nearby devices on Windows) and selects it.
4. Compare all three groups of numbers on both screens. Confirm on both devices only if they match; cancel if they differ.
5. The sender chooses which data to transfer and selects Prepare data (Confirm contents on Windows).
6. The receiver checks the vaults, direction and item counts, then chooses Accept this transfer (Accept contents on Windows). After acceptance, the sender chooses Start sending (Start transfer on Windows).
7. After complete receipt and validation, the receiver compares differences and confirms import as described above. The sender may now leave. Receipt does not mean the data has been imported into the vault.

If a LAN device is not found, the sender can expand Connect manually, enter an IPv4 address from the receiver’s waiting screen without a port, and choose Connect device. If connection still fails, check that the receiver is still waiting and check the network or system pairing. You can also try the other connection method.
A transfer sends data in one direction; it does not automatically make both vaults identical. The sending vault stays unchanged, and existing destination records not included in this transfer are not deleted. Master passwords, app settings and quick-unlock settings are not transferred.
Idle-lock and lock-on-leave are temporarily paused during transfer and validation. Keep the apps in the foreground where possible. Locking the phone or vault, switching vaults or quitting ends the transfer. The idle timer restarts afterwards and normal locking applies during comparison. After interruption or failed validation, start waiting and connect again, then check the new verification numbers. The transfer does not resume automatically.

## Manage vaults and change the master password

Open Settings → Manage vaults to create or select another vault. Save drafts before switching. The currently unlocked vault has a Rename action; enter its master password if requested and save.
To change a master password, make a backup first, then open Settings → Change master password. Enter the current password, enter the new password twice, then choose Change and lock. The vault locks after a successful change. Unlock it with the new password. Previously exported backups still use their original backup passwords. An empty new master password removes password protection and disables quick unlock.
To delete a vault, choose Delete vault in the vault list, verify that vault’s master password, then check the name and item counts before confirming. This deletes all data in that vault and cannot be directly undone. Another vault’s password cannot authorize it.
If the result of a change or deletion is unclear, reload the vault list or unlock again as prompted to check what happened. Keep the existing data. Do not try to resolve this by repeatedly deleting or clearing app data.

## Set up fingerprint or face unlock

1. Unlock the intended vault with its master password and open Settings → Quick unlock.
2. The vault must already have a master password. Enter it, choose Enable quick unlock and complete the system fingerprint or face check. Enable each vault separately.
3. You can then use quick unlock on that vault’s locked screen. Return to the same setting to disable it.

Available methods depend on the system prompt. Only system-approved strong fingerprint or face authentication is accepted; the phone’s password, pattern or PIN cannot replace it. If biometrics are unavailable or fail, enter the vault’s master password.
Enable quick unlock again after moving data to a new device. Keep remembering the master password and making backups instead of relying only on biometrics.

## Lock, switch apps and exit

Before leaving, tap the lock icon or choose Lock now in Settings. By default, the vault locks after five consecutive minutes without activity, including time in the background. Change it under Lock when idle in Settings.
Lock immediately when leaving is off by default. Switching apps hides the page; you can continue if you return before the vault locks. With this setting on, switching apps or opening recent apps locks the vault. Locking the phone, locking manually or switching to another vault clears unsaved drafts. Save first.
To exit, press system Back from Home to lock and return to My vaults. Press Back again as prompted from the vault list to exit. Pressing the phone’s Home button only moves Cangoo to the background.
Unlock again to continue after locking. Previous backup previews or transfer comparisons do not reopen automatically. The rules for pausing automatic locking during a transfer are explained under sending and receiving.

## Copy information and clear the clipboard

Use the appropriate copy button in an item’s details, then paste promptly where needed. Sensitive values are hidden by default; reveal them only when necessary. You can copy without revealing first.
In Settings, set Keep copied content to 5, 30 or 60 seconds. Cangoo then attempts to clear the current clipboard. While cleanup is pending, you can also choose Clear clipboard. Duration changes apply to the next copy; dismissing a message does not cancel cleanup.
Clearing may affect something you copied afterwards from elsewhere. Clear requested means a request was made; system restrictions or a closed app can prevent timely cleanup. Copies saved by keyboards, system history or other apps are not removed. Manage those in the relevant software.

## Adjust display and system settings

In Settings, change Language, Text size and Appearance. Appearance provides color palettes and light or dark modes. Select or save as prompted, then return to your work. The settings gear also gives access to these general preferences and Help while locked.
Permissions and system settings shows the app’s system status and lets you open the phone’s settings when needed. Available biometrics do not mean quick unlock is enabled for the current vault; configure it separately.
If a status cannot be read, check it in system settings. Battery and background restrictions can affect background work. Keep transfers in the foreground where possible; a normal status does not guarantee continuous background execution on every phone.

## Check for updates and get help

While connected to the internet, choose Check for updates in Settings or Help → About Cangoo. Automatic checks are enabled by default with a one-day interval (24 hours). After the chosen number of days has passed since the last check, Cangoo checks on the next startup. A failed check also starts this interval. You can change the interval, or turn automatic checks off and still check manually.
When a new version is found, read its notes and release page. You can ignore reminders for seven days or for that version; this affects only its automatic reminders on this device. Retry a failed check. Failure does not mean the app is up to date. Update checks connect to GitHub to read public release information. The requests contain no vault contents or master password. You decide whether to download and install.
Help also lets you read the open-source license and third-party notices again. The contact entry in About Cangoo opens through the system browser or a suitable app.
Before updating, replacing the phone, uninstalling or clearing app data, make and verify an independent encrypted backup. When asking for help, provide the app version, steps and an error message without secrets. Do not send real passwords, vaults, backup files or sensitive screenshots.

For security issues, follow the [security reporting instructions](../../SECURITY.md).
