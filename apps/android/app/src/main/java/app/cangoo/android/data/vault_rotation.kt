package app.cangoo.android.data

import android.database.Cursor
import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.system.StructStat
import android.util.AtomicFile
import app.cangoo.android.data.VaultDescriptorAuth.field
import kotlinx.coroutines.CancellationException
import net.zetetic.database.DatabaseErrorHandler
import net.zetetic.database.sqlcipher.SQLiteDatabase
import java.io.ByteArrayInputStream
import java.io.DataInputStream
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import java.util.UUID

internal enum class VaultRotationFailure { INVALID_INPUT, AUTHENTICATION, SESSION_CLOSED, CANCELLED, BIOMETRIC_UNAVAILABLE, RECOVERY_ASSETS, STORAGE }
internal enum class VaultCleanupCategory { OLD_CIPHERTEXT, DEVICE_BINDING, RETAINED_RECOVERY, OTHER_FILES, UNVERIFIED }
internal data class VaultCleanupStatus(val complete: Boolean, val paths: List<String>,
    val categories: Set<VaultCleanupCategory> = if (complete) emptySet() else setOf(VaultCleanupCategory.UNVERIFIED))
internal data class VaultBindingClaims(val aliases: List<String>, val complete: Boolean)
internal sealed interface VaultRotationResult {
    data object Rotated : VaultRotationResult
    data class NoCommit(val reason: VaultRotationFailure, val residual: List<String> = emptyList()) : VaultRotationResult
    data class Unknown(val residual: List<String>) : VaultRotationResult
    data class Residual(val paths: List<String>, val categories: Set<VaultCleanupCategory> = setOf(VaultCleanupCategory.UNVERIFIED)) : VaultRotationResult
}

/** 只在唯一存储互斥内、原连接关闭后运行；只在候选上换密，选择发布是唯一提交点。 */
internal object VaultRotation {
    private val preserveCorruptFile = DatabaseErrorHandler { _, _ -> }
    private const val PREPARE_DOMAIN = "cangoo-android-rotation-preparation"
    private const val CLEANUP_DOMAIN = "cangoo-android-rotation-cleanup"
    private const val CLEANUP_FILE = "cleanup.bin"
    private const val MAX_RECEIPT_BYTES = 16384
    private val dataNames = setOf("vault.db", "vault.db-journal", "vault.db-wal", "vault.db-shm")
    private val descriptorNames = setOf("manifest.json", "manifest.json.bak", "manifest.json.new", CLEANUP_FILE,
        "$CLEANUP_FILE.bak", "$CLEANUP_FILE.new")
    private val legacyRecoveryNames = setOf(VaultMigration.RECOVERY_DIRECTORY, ".pending_recovery_before_v3")
    private val recoveryNames = VaultMigration.recoveryNames
    private val recoveryFiles = setOf(VaultStore.DATABASE_FILE, VaultStore.MANIFEST_FILE)

    internal class Asset(val path: String, val device: Long, val inode: Long, val size: Long, val digest: ByteArray)
    internal class SourceProof(val database: Asset, val manifest: Asset)
    private class Directory(val path: String, val device: Long, val inode: Long)
    private enum class Kind { ROTATION, UPGRADE }
    private enum class HeldStage { NONE, HOLDING, EXITING }
    private data class Receipt(val domain: String, val id: String, val operation: String, val old: VaultLayoutSelection,
                          val next: VaultLayoutSelection, val rootDevice: Long, val rootInode: Long,
                          val directories: List<Directory>, val assets: List<Asset>, val newAlias: String? = null,
                          val aliasImported: Boolean = false, val oldAlias: String? = null,
                          val kind: Kind = Kind.ROTATION, val heldStage: HeldStage = HeldStage.NONE,
                          val heldDirectories: List<Directory> = emptyList(), val heldAssets: List<Asset> = emptyList(), val version: Int = 4)
    private class Cleanup(val status: VaultCleanupStatus, val stableUpgrade: Boolean = false)
    private class CurrentFailure(val original: Exception) : Exception(original)

    fun sourceProof(files: VaultResolvedFiles, guard: () -> Unit): SourceProof =
        SourceProof(asset(files.root, files.database, guard), asset(files.root, files.manifest, guard))

    fun verifySource(files: VaultResolvedFiles, metadata: Metadata, key: ByteArray, proof: SourceProof, guard: () -> Unit) {
        guard()
        val current = VaultLayout.resolve(files.root, metadata.id)
        if (current.selection != files.selection || !sameAsset(files.root, proof.database, guard) || !sameAsset(files.root, proof.manifest, guard)) unavailable()
        val saved = Metadata.read(current.manifest, metadata.id)
        if (!metadata.sameContent(saved)) unavailable()
        VaultDescriptorAuth.verify(key, saved, current.selection)
        open(current.database, key).use { verifyDatabase(it, guard) }
        guard()
    }

    suspend fun change(files: VaultResolvedFiles, id: String, metadata: Metadata, oldMaster: String?, newMaster: String?,
               oldKey: ByteArray, authenticator: VaultBiometricAuthenticator? = null, bindingEnabled: Boolean? = null,
               onStage: (VaultChangeStage) -> Unit = {}, guard: () -> Unit): VaultRotationResult {
        val root = files.root
        val operation = UUID.randomUUID().toString()
        val changingData = bindingEnabled == null
        val needsBinding = bindingEnabled == true || changingData && metadata.biometric != null && !newMaster.isNullOrEmpty()
        val next = VaultLayoutSelection(if (changingData) operation else files.selection.dataGroup, operation)
        val plannedAlias = if (needsBinding) VaultBiometric.plannedAlias(id, operation) else null
        val dataDirectory = File(root, "data_$operation")
        val descriptorParent = File(root, "descriptors")
        val descriptorDirectory = File(descriptorParent, operation)
        val preparation = File(root, "rotation_pending_$operation.bin")
        val nextDatabase = File(dataDirectory, VaultStore.DATABASE_FILE)
        val nextManifest = File(descriptorDirectory, VaultStore.MANIFEST_FILE)
        var receipt: Receipt? = null
        var publicationAttempted = false
        var committed = false
        val newKey = if (changingData) VaultCrypto.randomBytes(VaultCrypto.KEY_BYTES) else oldKey.copyOf()
        try {
            guard()
            onStage(VaultChangeStage.PREPARING)
            if (changingData && MessageDigest.isEqual(oldKey, newKey)) unavailable()
            if (needsBinding && authenticator == null) return VaultRotationResult.NoCommit(VaultRotationFailure.BIOMETRIC_UNAVAILABLE)
            if (plannedAlias != null && VaultBiometric.exists(plannedAlias)) throw VaultBiometricFailure()
            val pending = finishAll(files, id, oldKey, oldMaster, guard)
            val upgrade = if (pending.status.complete) null else {
                if (!changingData || oldMaster == null || !pending.stableUpgrade) {
                    return VaultRotationResult.NoCommit(VaultRotationFailure.RECOVERY_ASSETS, pending.status.paths)
                }
                readCleanupReceipt(File(files.manifest.parentFile, CLEANUP_FILE), oldKey, id).also {
                    if (it.kind != Kind.UPGRADE || it.next != files.selection) unavailable()
                    verifyEntries(root, it.directories, it.assets, false, guard)
                }
            }
            val upgradeProof = upgrade?.let { asset(root, File(files.manifest.parentFile, CLEANUP_FILE), guard) }
            val currentMetadata = Metadata.read(files.manifest, id)
            if (!metadata.sameContent(currentMetadata)) unavailable()
            VaultDescriptorAuth.verify(oldKey, currentMetadata, files.selection)
            if (oldMaster != null) {
                val currentKey = currentMetadata.unlock(oldMaster, files.selection)
                try { if (!MessageDigest.isEqual(oldKey, currentKey)) unavailable() } finally { currentKey.fill(0) }
            }
            if (VaultMigration.sourceVersion(files.database, oldKey, guard) != 4) unavailable()
            VaultMigration.checkLogs(files.database)
            val sourceDatabase = asset(root, files.database, guard)
            val sourceManifest = asset(root, files.manifest, guard)
            VaultLayout.bootstrap(root, id, guard)
            guard()
            if (VaultLayout.resolve(root, id).selection != files.selection) unavailable()
            val rootStat = directoryStat(root)
            if (changingData && !dataDirectory.mkdir()) unavailable()
            if (!descriptorParent.exists() && !descriptorParent.mkdir()) unavailable()
            directoryStat(descriptorParent)
            if (!descriptorDirectory.mkdir()) unavailable()
            receipt = Receipt(PREPARE_DOMAIN, id, operation, files.selection, next, rootStat.st_dev, rootStat.st_ino,
                (if (changingData) listOf(directory(root, dataDirectory)) else emptyList()) + directory(root, descriptorDirectory),
                emptyList(), plannedAlias)
            writeReceipt(preparation, receipt, oldKey)
            syncDirectory(descriptorParent); syncDirectory(root)
            if (changingData) {
                copy(files.database, nextDatabase, guard)
                if (!sameAsset(root, sourceDatabase, guard) || !sameAsset(root, sourceManifest, guard)) unavailable()
                guard()
                onStage(VaultChangeStage.REENCRYPTING)
                open(nextDatabase, oldKey, writable = true).use { candidate ->
                    verifyDatabase(candidate, guard); guard(); candidate.changePassword(newKey); guard()
                }
                VaultMigration.checkLogs(nextDatabase)
                onStage(VaultChangeStage.VERIFYING)
                compare(files.database, oldKey, nextDatabase, newKey, guard)
            } else open(files.database, oldKey).use { verifyDatabase(it, guard) }
            val primaryDirectories = requireNotNull(receipt).directories.filter { it.path.startsWith("data_") }
            val primaryAssets = preparedAssets(root, primaryDirectories, guard)
            if (changingData) {
                receipt = requireNotNull(receipt).copy(assets = primaryAssets)
                replaceReceipt(preparation, requireNotNull(receipt), oldKey)
            }
            val envelope = if (plannedAlias != null) {
                val created = VaultBiometric.create(id, next.dataGroup, plannedAlias, newKey) {
                    receipt = requireNotNull(receipt).copy(newAlias = plannedAlias, aliasImported = true)
                    replaceReceipt(preparation, requireNotNull(receipt), oldKey)
                }
                guard()
                onStage(VaultChangeStage.BIOMETRIC)
                val verified = VaultBiometric.decrypt(id, next.dataGroup, created,
                    if (changingData) VaultBiometricPurpose.REBUILD else VaultBiometricPurpose.ENABLE, requireNotNull(authenticator), guard)
                try { if (!MessageDigest.isEqual(verified, newKey)) unavailable() } finally { verified.fill(0) }
                created
            } else null
            // 系统认证往返后先复核已签证的候选，再增加恢复配套，不能重采样掩盖变化。
            verifyEntries(root, primaryDirectories, primaryAssets, false, guard)
            val heldDirectories = mutableListOf<Directory>()
            if (upgrade != null) {
                for (sourceDirectory in upgrade.directories) {
                    guard()
                    val source = path(root, sourceDirectory.path)
                    val target = File(dataDirectory, source.name)
                    if (!target.mkdir()) unavailable()
                    heldDirectories += directory(root, target)
                    receipt = requireNotNull(receipt).copy(directories = requireNotNull(receipt).directories + heldDirectories.last())
                    replaceReceipt(preparation, requireNotNull(receipt), oldKey)
                    verifyEntries(root, upgrade.directories, upgrade.assets, false, guard)
                    val originalDatabase = File(source, VaultStore.DATABASE_FILE)
                    val originalMetadata = Metadata.read(File(source, VaultStore.MANIFEST_FILE), id)
                    VaultMigration.authenticateDescriptor(originalMetadata, oldMaster, oldKey, files.selection, guard)
                    if (VaultMigration.readVersion(originalDatabase, oldKey, verifyContent = true) !in
                        VaultMigration.recoveryVersions(source.name)) unavailable()
                    val copied = File(target, VaultStore.DATABASE_FILE)
                    copy(originalDatabase, copied, guard)
                    open(copied, oldKey, writable = true).use { candidate ->
                        verifyDatabase(candidate, guard); guard(); candidate.changePassword(newKey); guard()
                    }
                    VaultMigration.checkLogs(copied)
                    compare(originalDatabase, oldKey, copied, newKey, guard)
                    val modern = originalMetadata.version == 2
                    val retainedMetadata = Metadata.create(id, originalMetadata.name, requireNotNull(newMaster), newKey,
                        if (modern) next else null, if (modern) envelope else null)
                    val verified = retainedMetadata.unlock(newMaster, if (modern) next else null)
                    try { if (!MessageDigest.isEqual(verified, newKey)) unavailable() } finally { verified.fill(0) }
                    retainedMetadata.write(File(target, VaultStore.MANIFEST_FILE), guard)
                    if (!retainedMetadata.sameContent(Metadata.read(File(target, VaultStore.MANIFEST_FILE), id))) unavailable()
                    syncFile(copied); syncDirectory(target)
                }
                verifyEntries(root, upgrade.directories, upgrade.assets, false, guard)
                if (!sameAsset(root, requireNotNull(upgradeProof), guard)) unavailable()
            }
            val dataDirectories = requireNotNull(receipt).directories.filter { it.path.startsWith("data_") }
            val verifiedDataAssets = preparedAssets(root, dataDirectories, guard).map { entry ->
                primaryAssets.firstOrNull { it.path == entry.path } ?: entry
            }
            if (changingData) {
                receipt = requireNotNull(receipt).copy(assets = verifiedDataAssets)
                replaceReceipt(preparation, requireNotNull(receipt), oldKey)
            }
            guard()
            if (!sameAsset(root, sourceDatabase, guard) || !sameAsset(root, sourceManifest, guard)) unavailable()
            val wrapped = if (newMaster != null) Metadata.create(id, metadata.name, newMaster, newKey, next, envelope)
                else metadata.rebind(next, newKey, envelope)
            if (newMaster != null) {
                val verified = wrapped.unlock(newMaster, next)
                try { if (!MessageDigest.isEqual(verified, newKey)) unavailable() } finally { verified.fill(0) }
            }
            wrapped.write(nextManifest, guard)
            val saved = Metadata.read(nextManifest, id)
            if (!wrapped.sameContent(saved)) unavailable()
            VaultDescriptorAuth.verify(newKey, saved, next)
            val assets = mutableListOf(sourceManifest)
            if (changingData) assets += sourceDatabase
            if (upgrade != null) {
                verifyEntries(root, upgrade.directories, upgrade.assets, false, guard)
                if (!sameAsset(root, requireNotNull(upgradeProof), guard)) unavailable()
                assets += upgrade.assets
                assets += upgradeProof
            }

            if (changingData) listOf("-journal", "-wal", "-shm").forEach { suffix ->
                val file = File(files.database.path + suffix)
                if (statOrMissing(file) != null) {
                    if (file.length() != 0L) unavailable()
                    assets += asset(root, file, guard)
                }
            }
            // 非秘密准备回执随后原位补全；新秘密只授权删除这份确切inode，不形成摘要循环。
            val preparationStat = regularStat(preparation)
            assets += Asset(preparation.name, preparationStat.st_dev, preparationStat.st_ino, 0, ByteArray(32))
            val oldDirectories = ((if (changingData) listOf(files.database.parentFile!!) else emptyList()) + files.manifest.parentFile!!)
                .distinct().filter { it != root }
            val cleanup = Receipt(CLEANUP_DOMAIN, id, operation, files.selection, next, rootStat.st_dev, rootStat.st_ino,
                oldDirectories.map { directory(root, it) } + (upgrade?.directories ?: emptyList()), assets, oldAlias = metadata.biometric?.alias,
                heldStage = if (upgrade == null) HeldStage.NONE else HeldStage.HOLDING, heldDirectories = heldDirectories,
                heldAssets = verifiedDataAssets.filter { entry -> heldDirectories.any { path(root, entry.path).parentFile == path(root, it.path) } })
            writeReceipt(File(descriptorDirectory, CLEANUP_FILE), cleanup, newKey)
            verifyPrepared(root, dataDirectories, verifiedDataAssets, guard)
            val candidateAssets = preparedAssets(root, requireNotNull(receipt).directories, guard)
            receipt = Receipt(PREPARE_DOMAIN, id, operation, files.selection, next, rootStat.st_dev, rootStat.st_ino,
                requireNotNull(receipt).directories, candidateAssets, plannedAlias, requireNotNull(receipt).aliasImported)
            replaceReceipt(preparation, receipt, oldKey)
            if (changingData) syncFile(nextDatabase)
            syncFile(nextManifest)
            if (changingData) syncDirectory(dataDirectory)
            syncDirectory(descriptorDirectory); syncDirectory(descriptorParent); syncDirectory(root)
            guard()
            if (!sameAsset(root, sourceDatabase, guard) || !sameAsset(root, sourceManifest, guard)) unavailable()
            VaultMigration.checkLogs(files.database)
            onStage(VaultChangeStage.PUBLISHING)
            publicationAttempted = true
            VaultLayout.publish(root, id, files.selection, next) {
                guard()
                if (!sameAsset(root, sourceDatabase, guard) || !sameAsset(root, sourceManifest, guard)) unavailable()
                verifyPrepared(root, requireNotNull(receipt).directories, candidateAssets, guard)
                if (upgrade != null) {
                    verifyEntries(root, upgrade.directories, upgrade.assets, false, guard)
                    if (!sameAsset(root, requireNotNull(upgradeProof), guard)) unavailable()
                }
                VaultMigration.checkLogs(files.database)
            }
            committed = true
            // 已发布的事实不再交给可取消上下文；只停止清理并报告残留。
            var publishedVerified = false
            return try {
                guard()
                val selected = VaultLayout.resolve(root, id)
                if (selected.selection != next) unavailable()
                val selectedMetadata = Metadata.read(selected.manifest, id)
                if (!wrapped.sameContent(selectedMetadata)) unavailable()
                VaultDescriptorAuth.verify(newKey, selectedMetadata, selected.selection)
                open(selected.database, newKey).use { verifyDatabase(it, guard) }
                publishedVerified = true
                onStage(VaultChangeStage.CLEANING)
                val residual = cleanup(root, cleanup, newKey, guard).status
                if (residual.complete) {
                    removeCleanupReceipt(root, File(descriptorDirectory, CLEANUP_FILE), newKey, id)
                    VaultRotationResult.Rotated
                } else VaultRotationResult.Residual(residual.paths, residual.categories)
            } catch (failure: Exception) {
                val residual = remaining(root, cleanup.assets.map { it.path } + cleanup.directories.map { it.path } +
                    cleanup.heldAssets.map { it.path } + cleanup.heldDirectories.map { it.path } + relative(root, File(descriptorDirectory, CLEANUP_FILE)))
                if (failure is CurrentFailure) VaultRotationResult.Unknown(residual)
                else if (publishedVerified || failure is CancellationException || failure is VaultException && failure.code == VaultError.SESSION_CLOSED) {
                    val known = runCatching { cleanupStatus(root, cleanup) }.getOrNull()
                    VaultRotationResult.Residual(residual, (known?.categories ?: emptySet()) + VaultCleanupCategory.UNVERIFIED)
                } else VaultRotationResult.Unknown(residual)
            }
        } catch (failure: Exception) {
            if (committed || publicationAttempted && failure is VaultException && failure.code == VaultError.COMMIT_UNCERTAIN) {
                return VaultRotationResult.Unknown(remaining(root, listOf(relative(root, dataDirectory), relative(root, descriptorDirectory), preparation.name)))
            }
            val residual = try {
                val owned = receipt
                if (owned == null) listOf(dataDirectory, descriptorDirectory).filter { it.exists() }.map { relative(root, it) }
                else {
                    val leftovers = removePrepared(root, owned, guard = {})
                    if (leftovers.isEmpty()) {
                        if (statOrMissing(preparation) != null) removeReceipt(root, preparation, owned, oldKey)
                        emptyList()
                    }
                    else leftovers + preparation.name
                }
            } catch (_: Exception) { listOf(relative(root, dataDirectory), relative(root, descriptorDirectory), preparation.name) }
            return VaultRotationResult.NoCommit(reason(failure), remaining(root, residual + pendingPaths(files)))
        } finally { newKey.fill(0) }
    }

    /** 当前库完整性失败拒绝会话；清理证明失败只交付明确的清理缺口。 */
    fun finishRecovery(files: VaultResolvedFiles, id: String, key: ByteArray, master: String?, guard: () -> Unit): VaultCleanupStatus =
        finishAll(files, id, key, master, guard).status

    private fun finishAll(files: VaultResolvedFiles, id: String, key: ByteArray, master: String?, guard: () -> Unit): Cleanup {
        guard()
        val root = files.root
        val selected = VaultLayout.resolve(root, id)
        if (selected.selection != files.selection || selected.database != files.database || selected.manifest != files.manifest) unavailable()
        val post = File(files.manifest.parentFile, CLEANUP_FILE)
        val inventory = try {
            val pending = root.listFiles()?.filter { it.name.startsWith("rotation_pending_") } ?: unavailable()
            (receiptPresent(post) || recoveryPaths(files).isNotEmpty()) to pending
        } catch (failure: CancellationException) { throw failure }
        catch (failure: CurrentFailure) { throw failure.original }
        catch (failure: VaultException) { if (failure.code == VaultError.SESSION_CLOSED) throw failure; null }
        catch (_: Exception) { null }
        if (inventory == null || inventory.first || inventory.second.isNotEmpty()) {
            // 主库/所选身份验证是授会话边界，不能与清理元数据失败一起吞成残留。
            try { verifyCurrent(files, id, key, guard, master) } catch (failure: CurrentFailure) { throw failure.original }
        }
        if (inventory == null) return Cleanup(VaultCleanupStatus(false, emptyList()))
        return try {
            if (!receiptPresent(post) && recoveryPaths(files).isNotEmpty() && inventory.second.isEmpty() && rotationPaths(files).isEmpty()) {
                val snapshots = VaultMigration.proveRecovery(files, id, master, key, guard)
                if (snapshots.isEmpty()) unavailable()
                val metadata = Metadata.read(files.manifest, id)
                VaultMigration.authenticateDescriptor(metadata, master, key, files.selection, guard)
                val rootStat = directoryStat(root)
                VaultLayout.bootstrap(root, id, guard)
                val receipt = Receipt(CLEANUP_DOMAIN, id, UUID.randomUUID().toString(), files.selection, files.selection,
                    rootStat.st_dev, rootStat.st_ino, snapshots.map { snapshotDirectory(root, it) },
                    snapshots.flatMap { snapshotAssets(root, it) }, kind = Kind.UPGRADE)
                verifyEntries(root, receipt.directories, receipt.assets, false, guard)
                writeReceipt(post, receipt, key)
            }
            if (receiptPresent(post)) {
                val receipt = readCleanupReceipt(post, key, id)
                if (receipt.next != files.selection) unavailable()
                val result = cleanup(root, receipt, key, guard)
                if (!result.status.complete) return result
                removeCleanupReceipt(root, post, key, id)
            }
            for (file in inventory.second) {
                if (statOrMissing(file) == null) continue
                guard()
                val receipt = readReceipt(file, key, PREPARE_DOMAIN, id)
                if (file.name != "rotation_pending_${receipt.operation}.bin" || receipt.old != files.selection ||
                    removePrepared(root, receipt, guard).isNotEmpty()) return Cleanup(VaultCleanupStatus(false, pendingPaths(files)))
                removeReceipt(root, file, receipt, key)
            }
            val paths = pendingPaths(files)
            Cleanup(VaultCleanupStatus(paths.isEmpty(), paths))
        } catch (failure: CancellationException) { throw failure }
        catch (failure: CurrentFailure) { throw failure.original }
        catch (failure: VaultException) { if (failure.code == VaultError.SESSION_CLOSED) throw failure; Cleanup(VaultCleanupStatus(false, safePendingPaths(files))) }
        catch (_: Exception) { Cleanup(VaultCleanupStatus(false, safePendingPaths(files))) }
    }

    private fun snapshotDirectory(root: File, snapshot: VaultMigration.RecoverySnapshot) = Directory(relative(root, snapshot.directory),
        snapshot.directoryStat.st_dev, snapshot.directoryStat.st_ino)
    private fun snapshotAssets(root: File, snapshot: VaultMigration.RecoverySnapshot) = listOf(
        Asset(relative(root, File(snapshot.directory, VaultStore.DATABASE_FILE)), snapshot.databaseStat.st_dev,
            snapshot.databaseStat.st_ino, snapshot.databaseStat.st_size, snapshot.databaseHash),
        Asset(relative(root, File(snapshot.directory, VaultStore.MANIFEST_FILE)), snapshot.manifestStat.st_dev,
            snapshot.manifestStat.st_ino, snapshot.manifestStat.st_size, snapshot.manifestHash))
    private fun recoveryPaths(files: VaultResolvedFiles) = recoveryNames.map { relative(files.root, File(files.database.parentFile, it)) }
        .filter { statOrMissing(path(files.root, it)) != null }
    private fun safePendingPaths(files: VaultResolvedFiles) = runCatching { pendingPaths(files) }.getOrDefault(emptyList())

    /** 删除只消费本库已认证的精确别名；未知回执不触发密钥库前缀扫描。 */
    fun deletionBindings(files: VaultResolvedFiles, id: String, key: ByteArray, guard: () -> Unit): VaultBindingClaims {
        guard()
        val aliases = mutableSetOf<String>()
        val metadata = Metadata.read(files.manifest, id)
        VaultDescriptorAuth.verify(key, metadata, files.selection)
        metadata.biometric?.alias?.let { aliases += it }
        var complete = true
        val covered = mutableSetOf<String>()
        var published: Receipt? = null
        val post = File(files.manifest.parentFile, CLEANUP_FILE)
        try {
            if (receiptPresent(post)) {
                val receipt = readCleanupReceipt(post, key, id)
                checkRoot(files.root, receipt)
                if (receipt.next != files.selection) unavailable()
                published = receipt
                receipt.oldAlias?.let { aliases += it }
                covered += receipt.assets.map { it.path } + receipt.directories.map { it.path }
                covered += relative(files.root, post)
            }
            val candidates = files.root.listFiles()?.filter { it.name.startsWith("rotation_pending_") } ?: unavailable()
            for (file in candidates) {
                guard()
                val committed = published
                val entry = committed?.assets?.singleOrNull { it.path == file.name }
                if (entry != null && matchesAsset(files.root, entry, committed.operation, guard)) continue
                val receipt = readReceipt(file, key, PREPARE_DOMAIN, id)
                checkRoot(files.root, receipt)
                if (receipt.old != files.selection || file.name != "rotation_pending_${receipt.operation}.bin") unavailable()
                if (receipt.aliasImported) receipt.newAlias?.let { aliases += it }
                else if (receipt.newAlias?.let(VaultBiometric::exists) == true) complete = false
                covered += receipt.assets.map { it.path } + receipt.directories.map { it.path } + file.name
            }
            if (rotationPaths(files).any { it !in covered }) complete = false
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { if (failure.code == VaultError.SESSION_CLOSED) throw failure; complete = false }
        catch (_: Exception) { complete = false }
        guard()
        return VaultBindingClaims(aliases.sorted(), complete)
    }

    internal fun pendingPaths(files: VaultResolvedFiles): List<String> = remaining(files.root, rotationPaths(files) +
        recoveryNames.map { relative(files.root, File(files.database.parentFile, it)) })

    private fun rotationPaths(files: VaultResolvedFiles): List<String> {
        val root = files.root
        val candidates = root.listFiles()?.filter { it.name.startsWith("rotation_pending_") ||
            it.name.startsWith("data_") && it != files.database.parentFile }?.map { it.name } ?: unavailable()
        val descriptorParent = File(root, "descriptors")
        val descriptors = if (statOrMissing(descriptorParent) == null) emptyList() else {
            directoryStat(descriptorParent)
            descriptorParent.listFiles()?.filter { it != files.manifest.parentFile }?.map { relative(root, it) } ?: unavailable()
        }
        val legacy = listOf("vault.db", "vault.db-journal", "vault.db-wal", "vault.db-shm", "manifest.json").filter {
            if (it.startsWith("vault.db")) files.selection.dataGroup != "legacy" else files.selection.descriptorGroup != "legacy"
        }
        return remaining(root, candidates + descriptors + legacy + listOf(CLEANUP_FILE, "$CLEANUP_FILE.bak", "$CLEANUP_FILE.new")
            .map { relative(root, File(files.manifest.parentFile, it)) })
    }

    private fun remaining(root: File, paths: List<String>): List<String> = paths.distinct().filter {
        if (it.startsWith("keystore:")) true else runCatching { statOrMissing(path(root, it)) != null }.getOrDefault(true)
    }

    private fun open(file: File, key: ByteArray, writable: Boolean = false): SQLiteDatabase {
        VaultDatabase.initializeNative()
        return SQLiteDatabase.openDatabase(file.absolutePath, key, null,
            (if (writable) SQLiteDatabase.OPEN_READWRITE else SQLiteDatabase.OPEN_READONLY) or
                SQLiteDatabase.NO_LOCALIZED_COLLATORS, preserveCorruptFile, null)
    }

    private fun verifyDatabase(database: SQLiteDatabase, guard: () -> Unit) {
        guard()
        database.query("PRAGMA cipher_status").use { if (!it.moveToFirst() || it.getInt(0) != 1 || it.moveToNext()) unavailable() }
        database.query("PRAGMA cipher_integrity_check").use { if (it.moveToFirst()) unavailable() }
        database.query("PRAGMA integrity_check").use { if (!it.moveToFirst() || it.getString(0) != "ok" || it.moveToNext()) unavailable() }
        database.query("PRAGMA foreign_key_check").use { if (it.moveToFirst()) unavailable() }
        guard()
    }

    internal fun compare(source: File, oldKey: ByteArray, candidate: File, newKey: ByteArray, guard: () -> Unit) {
        open(source, oldKey).use { original ->
            open(candidate, newKey).use { changed ->
                verifyDatabase(original, guard); verifyDatabase(changed, guard)
                listOf("user_version", "application_id", "auto_vacuum", "encoding").forEach { name ->
                    equalRows(original.query("PRAGMA $name"), changed.query("PRAGMA $name"), guard)
                }
                equalRows(original.query("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name,tbl_name"),
                    changed.query("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name,tbl_name"), guard)
                val tables = mutableListOf<String>()
                original.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").use { rows ->
                    while (rows.moveToNext()) { guard(); tables += rows.getString(0) }
                }
                for (table in tables) {
                    val quoted = "\"" + table.replace("\"", "\"\"") + "\""
                    equalRows(original.query("PRAGMA table_info($quoted)"), changed.query("PRAGMA table_info($quoted)"), guard)
                    val primaryKey = mutableListOf<Pair<Int, String>>()
                    original.query("PRAGMA table_info($quoted)").use { rows ->
                        while (rows.moveToNext()) { guard(); if (rows.getInt(5) > 0) primaryKey += rows.getInt(5) to rows.getString(1) }
                    }
                    val stableColumns = if (table == "sqlite_sequence") listOf("name") else primaryKey.sortedBy { it.first }.map { it.second }
                    if (stableColumns.isEmpty()) unavailable()
                    val order = stableColumns.joinToString(",") { "\"" + it.replace("\"", "\"\"") + "\"" }
                    equalRows(original.query("SELECT * FROM $quoted ORDER BY $order"), changed.query("SELECT * FROM $quoted ORDER BY $order"), guard)
                }
            }
        }
    }

    private fun equalRows(first: Cursor, second: Cursor, guard: () -> Unit) = first.use { left -> second.use { right ->
        if (!left.columnNames.contentEquals(right.columnNames)) unavailable()
        while (true) {
            guard()
            val next = left.moveToNext()
            if (next != right.moveToNext()) unavailable()
            if (!next) break
            for (index in 0 until left.columnCount) {
                val type = left.getType(index)
                if (type != right.getType(index)) unavailable()
                val equal = when (type) {
                    Cursor.FIELD_TYPE_NULL -> true
                    Cursor.FIELD_TYPE_INTEGER -> left.getLong(index) == right.getLong(index)
                    Cursor.FIELD_TYPE_FLOAT -> left.getDouble(index).toBits() == right.getDouble(index).toBits()
                    Cursor.FIELD_TYPE_STRING -> left.getString(index) == right.getString(index)
                    Cursor.FIELD_TYPE_BLOB -> {
                        val a = left.getBlob(index); val b = right.getBlob(index)
                        try { a.contentEquals(b) } finally { a.fill(0); b.fill(0) }
                    }
                    else -> false
                }
                if (!equal) unavailable()
            }
        }
    } }

    private fun cleanup(root: File, receipt: Receipt, key: ByteArray, guard: () -> Unit): Cleanup {
        checkRoot(root, receipt)
        if (VaultLayout.resolve(root, receipt.id).selection != receipt.next) unavailable()
        validateReceipt(receipt)
        val selected = VaultLayout.resolve(root, receipt.id)
        val activePaths = setOf(relative(root, selected.database), relative(root, selected.manifest), relative(root, File(selected.manifest.parentFile, CLEANUP_FILE)))
        if (receipt.assets.any { it.path in activePaths } || receipt.directories.any { path(root, it.path) == root ||
                path(root, it.path) == selected.database.parentFile || path(root, it.path) == selected.manifest.parentFile }) unavailable()
        if (receipt.heldStage != HeldStage.NONE) verifyEntries(root, receipt.heldDirectories, receipt.heldAssets,
            receipt.heldStage == HeldStage.EXITING, guard)
        verifyEntries(root, receipt.directories, receipt.assets, true, guard, receipt.operation)
        var deleted = false
        var removing = false
        try {
            for (entry in receipt.assets) {
                guard(); checkRoot(root, receipt)
                val file = path(root, entry.path)
                if (statOrMissing(file) == null) { syncDeletionParent(root, file); continue }
                if (!matchesAsset(root, entry, receipt.operation, guard)) unavailable()
                removing = true
                Os.remove(file.absolutePath)
                removing = false
                deleted = true
                syncDirectory(file.parentFile!!)
            }
            for (entry in receipt.directories.sortedByDescending { it.path.count { c -> c == '/' } }) {
                guard(); checkRoot(root, receipt)
                val file = path(root, entry.path)
                val stamp = statOrMissing(file)
                if (stamp == null) { syncDeletionParent(root, file); continue }
                if (!OsConstants.S_ISDIR(stamp.st_mode) || stamp.st_dev != entry.device || stamp.st_ino != entry.inode ||
                    file.listFiles()?.isEmpty() != true) unavailable()
                removing = true
                Os.remove(file.absolutePath)
                removing = false
                deleted = true
                syncDirectory(file.parentFile!!)
            }
        } catch (failure: ErrnoException) {
            // 仅明确的首次删除失败且完整证明仍成立，才允许改密承接这份升级配套。
            if (!deleted && removing && receipt.kind == Kind.UPGRADE) {
                verifyEntries(root, receipt.directories, receipt.assets, false, guard)
                val others = rotationPaths(selected).filter { it != relative(root, File(selected.manifest.parentFile, CLEANUP_FILE)) }
                if (others.isEmpty()) return Cleanup(cleanupStatus(root, receipt), true)
            }
            return Cleanup(cleanupStatus(root, receipt).let { it.copy(categories = it.categories + VaultCleanupCategory.UNVERIFIED) })
        }
        receipt.oldAlias?.let { alias ->
            guard()
            if (Metadata.read(selected.manifest, receipt.id).biometric?.alias == alias) unavailable()
            try { VaultBiometric.remove(receipt.id, alias) }
            catch (_: Exception) { return Cleanup(cleanupStatus(root, receipt, alias)) }
        }
        if (receipt.heldStage != HeldStage.NONE) {
            verifyCurrent(selected, receipt.id, key, guard)
            verifyEntries(root, receipt.heldDirectories, receipt.heldAssets, receipt.heldStage == HeldStage.EXITING, guard)
            if (receipt.heldStage == HeldStage.HOLDING) {
                atomicCleanupReceipt(File(selected.manifest.parentFile, CLEANUP_FILE), receipt.copy(heldStage = HeldStage.EXITING), key)
            }
            // EXITING的认证写入及父目录同步已确认，之后才允许缺件并继续清理。
            for (entry in receipt.heldAssets) {
                guard(); checkRoot(root, receipt)
                val file = path(root, entry.path)
                if (statOrMissing(file) == null) { syncDeletionParent(root, file); continue }
                if (!sameAsset(root, entry, guard)) unavailable()
                Os.remove(file.absolutePath); syncDirectory(file.parentFile!!)
            }
            for (entry in receipt.heldDirectories) {
                guard(); checkRoot(root, receipt)
                val file = path(root, entry.path)
                val stamp = statOrMissing(file)
                if (stamp == null) { syncDeletionParent(root, file); continue }
                if (!OsConstants.S_ISDIR(stamp.st_mode) || stamp.st_dev != entry.device || stamp.st_ino != entry.inode ||
                    file.listFiles()?.isEmpty() != true) unavailable()
                Os.remove(file.absolutePath); syncDirectory(file.parentFile!!)
            }
        }
        return Cleanup(VaultCleanupStatus(true, emptyList()))
    }

    private fun verifyCurrent(files: VaultResolvedFiles, id: String, key: ByteArray, guard: () -> Unit, master: String? = null) {
        try {
            val metadata = Metadata.read(files.manifest, id)
            VaultDescriptorAuth.verify(key, metadata, files.selection)
            if (master != null) {
                val authenticated = metadata.unlock(master, files.selection)
                try { if (!MessageDigest.isEqual(authenticated, key)) unavailable() }
                finally { authenticated.fill(0) }
            }
            val databaseBefore = regularStat(files.database)
            open(files.database, key).use { if (it.version != 4) unavailable(); verifyDatabase(it, guard) }
            if (!sameStamp(databaseBefore, regularStat(files.database)) || VaultLayout.resolve(files.root, id).selection != files.selection ||
                !metadata.sameContent(Metadata.read(files.manifest, id))) unavailable()
            guard()
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { if (failure.code == VaultError.SESSION_CLOSED) throw failure; throw CurrentFailure(failure) }
        catch (failure: Exception) { throw CurrentFailure(failure) }
    }

    private fun cleanupStatus(root: File, receipt: Receipt, alias: String? = null): VaultCleanupStatus {
        val paths = remaining(root, receipt.assets.map { it.path } + receipt.directories.map { it.path })
        val held = remaining(root, receipt.heldAssets.map { it.path } + receipt.heldDirectories.map { it.path })
        val categories = mutableSetOf<VaultCleanupCategory>()
        val pendingAlias = alias ?: receipt.oldAlias?.takeIf { saved ->
            try { VaultBiometric.exists(saved) } catch (_: Exception) { categories += VaultCleanupCategory.UNVERIFIED; false }
        }
        if (paths.isNotEmpty()) {
            if (receipt.kind == Kind.UPGRADE) categories += VaultCleanupCategory.RETAINED_RECOVERY
            else {
                val oldData = dataPrefix(receipt.old)
                if (receipt.old.dataGroup != receipt.next.dataGroup && paths.any { it.startsWith(oldData + "vault.db") ||
                        recoveryNames.any { name -> it.startsWith(oldData + name + "/") || it == oldData + name } ||
                        it == oldData.removeSuffix("/") || it.endsWith("manifest.json") }) categories += VaultCleanupCategory.OLD_CIPHERTEXT
                if (categories.isEmpty()) categories += VaultCleanupCategory.OTHER_FILES
            }
        }
        if (held.isNotEmpty()) categories += VaultCleanupCategory.RETAINED_RECOVERY
        if (pendingAlias != null) categories += VaultCleanupCategory.DEVICE_BINDING
        if (categories.isEmpty()) categories += VaultCleanupCategory.OTHER_FILES
        return VaultCleanupStatus(false, paths + held + listOfNotNull(pendingAlias?.let { "keystore:$it" }), categories)
    }

    private fun dataPrefix(selection: VaultLayoutSelection) = if (selection.dataGroup == "legacy") "" else "data_${selection.dataGroup}/"
    private fun descriptorPrefix(selection: VaultLayoutSelection) = if (selection.descriptorGroup == "legacy") "" else "descriptors/${selection.descriptorGroup}/"
    private fun recoveryDirectoryPaths(selection: VaultLayoutSelection, version: Int = 4) =
        (if (version < 4) legacyRecoveryNames else recoveryNames).map { dataPrefix(selection) + it }.toSet()

    private fun matchesAsset(root: File, entry: Asset, operation: String, guard: () -> Unit): Boolean =
        if (entry.path == "rotation_pending_$operation.bin" && entry.size == 0L && entry.digest.all { it == 0.toByte() }) {
            regularStat(path(root, entry.path)).let { it.st_dev == entry.device && it.st_ino == entry.inode }
        } else sameAsset(root, entry, guard)

    private fun verifyEntries(root: File, directories: List<Directory>, assets: List<Asset>, allowMissing: Boolean,
                              guard: () -> Unit, operation: String = "") {
        for (entry in directories) {
            guard()
            val file = path(root, entry.path)
            val stamp = statOrMissing(file)
            if (stamp == null) { if (!allowMissing) unavailable(); continue }
            if (!OsConstants.S_ISDIR(stamp.st_mode) || stamp.st_dev != entry.device || stamp.st_ino != entry.inode) unavailable()
            val expected = assets.filter { path(root, it.path).parentFile == file }.map { it.path } +
                directories.filter { path(root, it.path).parentFile == file }.map { it.path }
            val actual = file.listFiles()?.map { relative(root, it) }?.toSet() ?: unavailable()
            if (actual.any { it !in expected } || !allowMissing && actual != expected.toSet()) unavailable()
        }
        for (entry in assets) {
            guard()
            if (statOrMissing(path(root, entry.path)) == null) { if (!allowMissing) unavailable(); continue }
            if (!matchesAsset(root, entry, operation, guard)) unavailable()
        }
    }

    private fun oldAssetPaths(receipt: Receipt): Set<String> {
        val data = if (receipt.old.dataGroup == "legacy") "" else "data_${receipt.old.dataGroup}/"
        val descriptor = if (receipt.old.descriptorGroup == "legacy") "" else "descriptors/${receipt.old.descriptorGroup}/"
        return (if (receipt.old.dataGroup != receipt.next.dataGroup) dataNames.map { data + it }.toSet() else emptySet()) +
            descriptorNames.map { descriptor + it } + "rotation_pending_${receipt.operation}.bin" +
            receipt.directories.filter { it.path in recoveryDirectoryPaths(receipt.old, receipt.version) }.flatMap { directory -> recoveryFiles.map { "${directory.path}/$it" } }
    }

    private fun validateReceipt(receipt: Receipt) {
        require(receipt.domain in setOf(PREPARE_DOMAIN, CLEANUP_DOMAIN) && VaultDescriptorAuth.validUuid(receipt.id) &&
            VaultDescriptorAuth.validUuid(receipt.operation) && listOf(receipt.old.dataGroup, receipt.old.descriptorGroup,
                receipt.next.dataGroup, receipt.next.descriptorGroup).all(VaultDescriptorAuth::validGroup))
        require(receipt.version in 1..4)
        val recoveryCount = if (receipt.version < 4) legacyRecoveryNames.size else recoveryNames.size
        require(receipt.directories.size <= (if (receipt.version < 3) 2 else 2 + recoveryCount) &&
            receipt.heldDirectories.size <= recoveryCount &&
            receipt.assets.size + receipt.heldAssets.size <= (if (receipt.version < 4) 16 else
                dataNames.size + descriptorNames.size + 1 + 2 * recoveryCount * recoveryFiles.size))
        val allDirectories = receipt.directories + receipt.heldDirectories
        val allAssets = receipt.assets + receipt.heldAssets
        require(allDirectories.map { it.path }.distinct().size == allDirectories.size && allAssets.map { it.path }.distinct().size == allAssets.size)
        require(allDirectories.all { it.device >= 0 && it.inode >= 0 } && allAssets.all { it.device >= 0 && it.inode >= 0 && it.size >= 0 && it.digest.size == 32 })
        require(receipt.newAlias == null && !receipt.aliasImported || receipt.newAlias == VaultBiometric.plannedAlias(receipt.id, receipt.operation))
        require(receipt.oldAlias == null || VaultDescriptorAuth.validAlias(receipt.oldAlias) &&
            receipt.oldAlias.startsWith("cangoo_vault_${receipt.id}_"))
        fun paired(directories: List<Directory>, assets: List<Asset>) = directories.all { directory ->
            assets.filter { it.path.startsWith("${directory.path}/") }.map { it.path.removePrefix("${directory.path}/") }.toSet() == recoveryFiles
        }
        if (receipt.kind == Kind.UPGRADE) {
            require(receipt.domain == CLEANUP_DOMAIN && receipt.old == receipt.next && receipt.newAlias == null &&
                !receipt.aliasImported && receipt.oldAlias == null && receipt.heldStage == HeldStage.NONE &&
                receipt.heldDirectories.isEmpty() && receipt.heldAssets.isEmpty() && receipt.directories.isNotEmpty())
            require(receipt.directories.all { it.path in recoveryDirectoryPaths(receipt.next, receipt.version) } &&
                receipt.assets.size == receipt.directories.size * 2 && paired(receipt.directories, receipt.assets))
            return
        }
        require(receipt.old != receipt.next && receipt.next.descriptorGroup == receipt.operation &&
            (receipt.next.dataGroup == receipt.operation || receipt.next.dataGroup == receipt.old.dataGroup))
        val changedData = receipt.old.dataGroup != receipt.next.dataGroup
        if (receipt.domain == PREPARE_DOMAIN) {
            val base = (if (changedData) setOf("data_${receipt.next.dataGroup}") else emptySet()) + "descriptors/${receipt.next.descriptorGroup}"
            val recovery = receipt.directories.filter { it.path in recoveryDirectoryPaths(receipt.next, receipt.version) }.map { it.path }.toSet()
            require(recovery.isEmpty() || changedData)
            require(receipt.directories.map { it.path }.toSet() == base + recovery && receipt.oldAlias == null &&
                receipt.heldStage == HeldStage.NONE && receipt.heldDirectories.isEmpty() && receipt.heldAssets.isEmpty())
            val allowed = (if (changedData) dataNames.map { dataPrefix(receipt.next) + it } else emptyList()) +
                descriptorNames.map { descriptorPrefix(receipt.next) + it } + recovery.flatMap { directory -> recoveryFiles.map { "$directory/$it" } }
            require(receipt.assets.all { it.path in allowed })
        } else {
            require(receipt.newAlias == null && !receipt.aliasImported)
            val base = listOfNotNull(receipt.old.dataGroup.takeUnless { it == "legacy" || !changedData }?.let { "data_$it" },
                receipt.old.descriptorGroup.takeUnless { it == "legacy" }?.let { "descriptors/$it" }).toSet()
            val recovery = receipt.directories.filter { it.path in recoveryDirectoryPaths(receipt.old, receipt.version) }
            require(recovery.isEmpty() || changedData)
            require(receipt.directories.map { it.path }.toSet() == base + recovery.map { it.path } && paired(recovery, receipt.assets))
            require(receipt.assets.all { it.path in oldAssetPaths(receipt) })
            if (receipt.heldStage == HeldStage.NONE) require(receipt.heldDirectories.isEmpty() && receipt.heldAssets.isEmpty())
            else {
                require(changedData && recovery.isNotEmpty() && receipt.heldDirectories.map { it.path }.toSet() ==
                    recovery.map { dataPrefix(receipt.next) + it.path.substringAfterLast('/') }.toSet())
                require(receipt.heldAssets.size == receipt.heldDirectories.size * 2 && paired(receipt.heldDirectories, receipt.heldAssets))
            }
        }
    }

    private fun preparedAssets(root: File, directories: List<Directory>, guard: () -> Unit): List<Asset> = directories.flatMap { entry ->
        guard()
        val directory = path(root, entry.path)
        val before = directoryStat(directory)
        if (before.st_dev != entry.device || before.st_ino != entry.inode) unavailable()
        val names = if (entry.path.substringAfterLast('/') in recoveryNames) recoveryFiles else if (entry.path.startsWith("data_")) dataNames else descriptorNames
        val files = directory.listFiles() ?: unavailable()
        val childDirectories = directories.filter { path(root, it.path).parentFile == directory }.map { path(root, it.path) }.toSet()
        val assets = files.filter { it !in childDirectories }.map { file -> if (file.name !in names) unavailable(); asset(root, file, guard) }
        val after = directoryStat(directory)
        if (after.st_dev != entry.device || after.st_ino != entry.inode ||
            directory.listFiles()?.map { relative(root, it) }?.toSet() != assets.map { it.path }.toSet() + childDirectories.map { relative(root, it) }) unavailable()
        assets
    }

    private fun verifyPrepared(root: File, directories: List<Directory>, expected: List<Asset>, guard: () -> Unit) {
        val actual = preparedAssets(root, directories, guard)
        if (actual.size != expected.size || actual.any { current -> expected.none { saved ->
                current.path == saved.path && current.device == saved.device && current.inode == saved.inode &&
                    current.size == saved.size && MessageDigest.isEqual(current.digest, saved.digest)
            } }) unavailable()
    }

    private fun removePrepared(root: File, receipt: Receipt, guard: () -> Unit): List<String> {
        checkRoot(root, receipt)
        validateReceipt(receipt)
        if (VaultLayout.resolve(root, receipt.id).selection != receipt.old || receipt.next == receipt.old ||
            receipt.domain != PREPARE_DOMAIN || receipt.kind != Kind.ROTATION) unavailable()
        val residual = mutableListOf<String>()
        val proven = try { verifyEntries(root, receipt.directories, receipt.assets, true, guard); true }
            catch (failure: CancellationException) { throw failure }
            catch (_: Exception) { false }
        for (entry in receipt.directories.sortedByDescending { it.path.count { c -> c == '/' } }) {
            guard(); checkRoot(root, receipt)
            val directory = path(root, entry.path)
            val stamp = statOrMissing(directory) ?: continue
            if (!OsConstants.S_ISDIR(stamp.st_mode) || stamp.st_dev != entry.device || stamp.st_ino != entry.inode) { residual += entry.path; continue }
            if (!proven) { residual += entry.path; continue }
            val owned = receipt.assets.filter { path(root, it.path).parentFile == directory }
            owned.forEach { expected ->
                val file = path(root, expected.path)
                if (statOrMissing(file) == null) return@forEach
                guard(); checkRoot(root, receipt)
                val now = directoryStat(directory)
                if (now.st_dev != entry.device || now.st_ino != entry.inode || !sameAsset(root, expected, guard)) unavailable()
                Os.remove(file.absolutePath)
            }
            if (directory.listFiles()?.isEmpty() != true) { residual += entry.path; continue }
            Os.remove(directory.absolutePath); syncDirectory(directory.parentFile!!)
        }
        receipt.newAlias?.let { alias ->
            guard()
            if (Metadata.read(VaultLayout.resolve(root, receipt.id).manifest, receipt.id).biometric?.alias == alias) unavailable()
            if (!receipt.aliasImported && VaultBiometric.exists(alias)) residual += "keystore:$alias"
            else if (receipt.aliasImported) {
                try { VaultBiometric.remove(receipt.id, alias) }
                catch (_: Exception) { residual += "keystore:$alias" }
            }
        }
        return residual
    }

    private fun writeReceipt(file: File, receipt: Receipt, key: ByteArray) {
        val payload = encodeReceipt(receipt)
        val mac = VaultDescriptorAuth.mac(key, payload.copyOf())
        val content = payload + mac
        try {
            val fd = Os.open(file.absolutePath, OsConstants.O_WRONLY or OsConstants.O_CREAT or OsConstants.O_EXCL or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0x180)
            try {
                var position = 0
                while (position < content.size) { val size = Os.write(fd, content, position, content.size - position); check(size > 0); position += size }
                Os.fsync(fd)
            } finally { Os.close(fd) }
            readReceipt(file, key, receipt.domain, receipt.id)
            syncDirectory(file.parentFile!!)
        } finally { payload.fill(0); mac.fill(0); content.fill(0) }
    }

    private fun replaceReceipt(file: File, receipt: Receipt, key: ByteArray) {
        val current = readReceipt(file, key, receipt.domain, receipt.id)
        require(current.operation == receipt.operation && current.old == receipt.old && current.next == receipt.next)
        val before = regularStat(file)
        val payload = encodeReceipt(receipt)
        val mac = VaultDescriptorAuth.mac(key, payload.copyOf())
        val bytes = payload + mac
        val descriptor = Os.open(file.absolutePath, OsConstants.O_WRONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        try {
            if (!sameStamp(before, Os.fstat(descriptor))) unavailable()
            Os.ftruncate(descriptor, 0)
            var position = 0
            while (position < bytes.size) { val count = Os.write(descriptor, bytes, position, bytes.size - position); check(count > 0); position += count }
            Os.fsync(descriptor)
            readReceipt(file, key, receipt.domain, receipt.id)
        } finally { payload.fill(0); mac.fill(0); bytes.fill(0); Os.close(descriptor) }
    }

    private fun encodeReceipt(receipt: Receipt): ByteArray {
        validateReceipt(receipt)
        return VaultDescriptorAuth.encoding(receipt.domain, receipt.version) {
        field(receipt.id); field(receipt.operation)
        field(receipt.old.dataGroup); field(receipt.old.descriptorGroup); field(receipt.next.dataGroup); field(receipt.next.descriptorGroup)
        field(receipt.rootDevice.toString()); field(receipt.rootInode.toString())
        writeInt(receipt.directories.size)
        receipt.directories.forEach { field(it.path); field(it.device.toString()); field(it.inode.toString()) }
        writeInt(receipt.assets.size)
        receipt.assets.forEach { field(it.path); field(it.device.toString()); field(it.inode.toString()); field(it.size.toString()); field(it.digest) }
        field(receipt.newAlias ?: ""); writeBoolean(receipt.aliasImported); field(receipt.oldAlias ?: "")
        field(receipt.kind.name); field(receipt.heldStage.name)
        writeInt(receipt.heldDirectories.size)
        receipt.heldDirectories.forEach { field(it.path); field(it.device.toString()); field(it.inode.toString()) }
        writeInt(receipt.heldAssets.size)
        receipt.heldAssets.forEach { field(it.path); field(it.device.toString()); field(it.inode.toString()); field(it.size.toString()); field(it.digest) }
        }.also { require(it.size + 32 <= MAX_RECEIPT_BYTES) }
    }

    private fun readReceipt(file: File, key: ByteArray, domain: String, id: String): Receipt {
        return try {
            val bytes = readBytes(file, MAX_RECEIPT_BYTES)
            try {
                if (bytes.size <= 32) unavailable()
                val payload = bytes.copyOfRange(0, bytes.size - 32)
                try {
                    val actual = bytes.copyOfRange(bytes.size - 32, bytes.size)
                    val expected = VaultDescriptorAuth.mac(key, payload.copyOf())
                    try { if (!MessageDigest.isEqual(actual, expected)) unavailable() }
                    finally { actual.fill(0); expected.fill(0) }
                    DataInputStream(ByteArrayInputStream(payload)).use { input ->
                        fun field(max: Int = 512): ByteArray { val size = input.readInt(); require(size in 0..max); return ByteArray(size).also(input::readFully) }
                        fun text(): String = field().let { value -> try { value.decodeToString(throwOnInvalidSequence = true) } finally { value.fill(0) } }
                        fun number(): Long = text().let { require(it.matches(Regex("0|[1-9][0-9]*"))); it.toLong() }
                        require(text() == domain)
                        val version = input.readInt(); require(version in 1..4 && text() == id)
                        val operation = text(); require(VaultDescriptorAuth.validUuid(operation))
                        val old = VaultLayoutSelection(text(), text()); val next = VaultLayoutSelection(text(), text())
                        require(VaultDescriptorAuth.validGroup(old.dataGroup) && VaultDescriptorAuth.validGroup(old.descriptorGroup) &&
                            VaultDescriptorAuth.validGroup(next.dataGroup) && VaultDescriptorAuth.validGroup(next.descriptorGroup))
                        if (version < 3) require(old != next && next.descriptorGroup == operation &&
                            (next.dataGroup == operation || version == 2 && next.dataGroup == old.dataGroup))
                        val device = number(); val inode = number()
                        val directories = (0 until input.readInt().also { require(it in 0..if (version < 3) 2 else if (version == 3) 4 else 2 + recoveryNames.size) }).map { Directory(text(), number(), number()) }
                        val assets = (0 until input.readInt().also { require(it in 0..if (version < 4) 16 else dataNames.size + descriptorNames.size + 1 + 2 * recoveryNames.size * recoveryFiles.size) }).map { Asset(text(), number(), number(), number(), field(32).also { require(it.size == 32) }) }
                        val newAlias = if (version >= 2) text().takeUnless { it.isEmpty() } else null
                        val imported = if (version >= 2) input.readUnsignedByte().also { require(it in 0..1) } == 1 else false
                        val oldAlias = if (version >= 2) text().takeUnless { it.isEmpty() } else null
                        require(newAlias == null && !imported || newAlias == VaultBiometric.plannedAlias(id, operation))
                        require(oldAlias == null || VaultDescriptorAuth.validAlias(oldAlias))
                        val kind = if (version >= 3) Kind.valueOf(text()) else Kind.ROTATION
                        val heldStage = if (version >= 3) HeldStage.valueOf(text()) else HeldStage.NONE
                        val heldDirectories = if (version >= 3) (0 until input.readInt().also { require(it in 0..if (version == 3) 2 else recoveryNames.size) }).map {
                            Directory(text(), number(), number()) } else emptyList()
                        val heldAssets = if (version >= 3) (0 until input.readInt().also { require(it in 0..if (version == 3) 16 else recoveryNames.size * recoveryFiles.size) }).map {
                            Asset(text(), number(), number(), number(), field(32).also { require(it.size == 32) }) } else emptyList()
                        require(input.available() == 0)
                        Receipt(domain, id, operation, old, next, device, inode, directories, assets, newAlias, imported, oldAlias,
                            kind, heldStage, heldDirectories, heldAssets, version).also(::validateReceipt)
                    }
                } finally { payload.fill(0) }
            } finally { bytes.fill(0) }
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { throw failure }
        catch (_: Exception) { unavailable() }
    }

    private fun receiptPresent(file: File): Boolean = listOf(file, File(file.path + ".bak"), File(file.path + ".new"))
        .any { statOrMissing(it) != null }

    private fun checkReceiptFiles(file: File) {
        directoryStat(file.parentFile!!)
        listOf(file, File(file.path + ".bak"), File(file.path + ".new")).forEach { part ->
            statOrMissing(part)?.let { if (!OsConstants.S_ISREG(it.st_mode)) unavailable() }
        }
    }

    private fun readCleanupReceipt(file: File, key: ByteArray, id: String): Receipt {
        checkReceiptFiles(file)
        AtomicFile(file).openRead().close()
        checkReceiptFiles(file)
        if (statOrMissing(File(file.path + ".bak")) != null || statOrMissing(File(file.path + ".new")) != null) unavailable()
        val receipt = readReceipt(file, key, CLEANUP_DOMAIN, id)
        syncFile(file); syncDirectory(file.parentFile!!)
        return receipt
    }

    private fun atomicCleanupReceipt(file: File, receipt: Receipt, key: ByteArray) {
        val current = readCleanupReceipt(file, key, receipt.id)
        val expected = encodeReceipt(current.copy(heldStage = HeldStage.EXITING))
        val payload = encodeReceipt(receipt)
        try { if (current.heldStage != HeldStage.HOLDING || !expected.contentEquals(payload)) unavailable() }
        finally { expected.fill(0) }
        val mac = VaultDescriptorAuth.mac(key, payload.copyOf())
        val bytes = payload + mac
        val atomic = AtomicFile(file)
        val output = atomic.startWrite()
        var committed = false
        try {
            checkReceiptFiles(file)
            val temporary = regularStat(File(file.path + ".new"))
            if (!sameStamp(temporary, Os.fstat(output.fd))) unavailable()
            output.write(bytes); output.fd.sync()
            checkReceiptFiles(file)
            if (!sameStamp(Os.fstat(output.fd), regularStat(File(file.path + ".new")))) unavailable()
            committed = true
            atomic.finishWrite(output)
            val read = encodeReceipt(readCleanupReceipt(file, key, receipt.id))
            try { if (!read.contentEquals(payload)) unavailable() } finally { read.fill(0) }
            syncDirectory(file.parentFile!!)
        } catch (failure: Exception) {
            if (!committed) atomic.failWrite(output)
            throw failure
        } finally { payload.fill(0); mac.fill(0); bytes.fill(0) }
    }

    private fun removeCleanupReceipt(root: File, file: File, key: ByteArray, id: String) =
        removeReceipt(root, file, readCleanupReceipt(file, key, id), key)

    private fun removeReceipt(root: File, file: File, receipt: Receipt, key: ByteArray) {
        checkRoot(root, receipt)
        val before = regularStat(file)
        val read = readReceipt(file, key, receipt.domain, receipt.id)
        val actual = encodeReceipt(read); val expected = encodeReceipt(receipt)
        try { if (!actual.contentEquals(expected) || !sameStamp(before, regularStat(file))) unavailable() }
        finally { actual.fill(0); expected.fill(0) }
        Os.remove(file.absolutePath); syncDirectory(file.parentFile!!)
    }

    private fun directory(root: File, file: File): Directory = directoryStat(file).let { Directory(relative(root, file), it.st_dev, it.st_ino) }
    private fun asset(root: File, file: File, guard: () -> Unit): Asset {
        val before = regularStat(file)
        val digest = MessageDigest.getInstance("SHA-256")
        val fd = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        val buffer = ByteArray(65536)
        try {
            if (!sameStamp(before, Os.fstat(fd))) unavailable()
            var size = 0L
            while (true) {
                guard()
                val count = Os.read(fd, buffer, 0, buffer.size)
                if (count == 0) break
                digest.update(buffer, 0, count); size = Math.addExact(size, count.toLong())
            }
            if (size != before.st_size || !sameStamp(before, Os.fstat(fd)) || !sameStamp(before, regularStat(file))) unavailable()
            return Asset(relative(root, file), before.st_dev, before.st_ino, before.st_size, digest.digest())
        } finally { buffer.fill(0); Os.close(fd) }
    }

    private fun sameAsset(root: File, expected: Asset, guard: () -> Unit): Boolean {
        val actual = asset(root, path(root, expected.path), guard)
        return actual.device == expected.device && actual.inode == expected.inode && actual.size == expected.size &&
            MessageDigest.isEqual(actual.digest, expected.digest)
    }

    private fun copy(source: File, destination: File, guard: () -> Unit) {
        val before = regularStat(source)
        val input = Os.open(source.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        val output = try { Os.open(destination.absolutePath, OsConstants.O_WRONLY or OsConstants.O_CREAT or OsConstants.O_EXCL or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0x180) }
            catch (failure: Exception) { Os.close(input); throw failure }
        val buffer = ByteArray(65536)
        try {
            if (!sameStamp(before, Os.fstat(input))) unavailable()
            var total = 0L
            while (true) {
                guard()
                val count = Os.read(input, buffer, 0, buffer.size)
                if (count == 0) break
                var position = 0
                while (position < count) { guard(); val wrote = Os.write(output, buffer, position, count - position); check(wrote > 0); position += wrote }
                total = Math.addExact(total, count.toLong())
            }
            if (total != before.st_size || !sameStamp(before, Os.fstat(input)) || !sameStamp(before, regularStat(source))) unavailable()
            Os.fsync(output)
        } finally { buffer.fill(0); try { Os.close(output) } finally { Os.close(input) } }
    }

    private fun readBytes(file: File, limit: Int): ByteArray {
        val before = regularStat(file)
        require(before.st_size in 1..limit.toLong())
        val fd = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        val bytes = ByteArray(limit + 1)
        try {
            if (!sameStamp(before, Os.fstat(fd))) unavailable()
            var position = 0
            while (position < bytes.size) { val count = Os.read(fd, bytes, position, bytes.size - position); if (count == 0) break; position += count }
            if (position.toLong() != before.st_size || !sameStamp(before, Os.fstat(fd)) || !sameStamp(before, regularStat(file))) unavailable()
            return bytes.copyOf(position)
        } finally { bytes.fill(0); Os.close(fd) }
    }

    private fun syncFile(file: File) {
        val before = regularStat(file)
        val fd = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        try { if (!sameStamp(before, Os.fstat(fd))) unavailable(); Os.fsync(fd); if (!sameStamp(before, regularStat(file))) unavailable() }
        finally { Os.close(fd) }
    }

    private fun syncDeletionParent(root: File, file: File) {
        var parent = file.parentFile ?: unavailable()
        while (statOrMissing(parent) == null) {
            if (parent == root || !parent.toPath().startsWith(root.toPath())) unavailable()
            parent = parent.parentFile ?: unavailable()
        }
        directoryStat(parent)
        syncDirectory(parent)
    }

    private fun relative(root: File, file: File): String {
        if (file.canonicalFile != file.absoluteFile || !file.toPath().startsWith(root.toPath()) || file == root) unavailable()
        return root.toPath().relativize(file.toPath()).toString().replace(File.separatorChar, '/')
    }
    private fun path(root: File, relative: String): File {
        if (relative.isEmpty() || relative.startsWith('/') || relative.split('/').any { it.isEmpty() || it == "." || it == ".." } || '\\' in relative) unavailable()
        return File(root, relative).also { if (relative(root, it) != relative) unavailable() }
    }
    private fun statOrMissing(file: File): StructStat? {
        if (file.canonicalFile != file.absoluteFile || Files.isSymbolicLink(file.toPath())) unavailable()
        return try { Os.lstat(file.absolutePath).also { if (OsConstants.S_ISLNK(it.st_mode)) unavailable() } }
        catch (failure: ErrnoException) { if (failure.errno == OsConstants.ENOENT) null else throw failure }
    }
    private fun regularStat(file: File): StructStat = (statOrMissing(file) ?: unavailable()).also { if (!OsConstants.S_ISREG(it.st_mode)) unavailable() }
    private fun directoryStat(file: File): StructStat = (statOrMissing(file) ?: unavailable()).also { if (!OsConstants.S_ISDIR(it.st_mode)) unavailable() }
    private fun checkRoot(root: File, receipt: Receipt) {
        if (root.name != receipt.id || directoryStat(root).let { it.st_dev != receipt.rootDevice || it.st_ino != receipt.rootInode }) unavailable()
    }
    private fun sameStamp(a: StructStat, b: StructStat) = a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_size == b.st_size &&
        a.st_mode == b.st_mode && a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
        a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
    private fun unavailable(): Nothing = throw VaultException(VaultError.DATA_UNAVAILABLE)
    fun reason(failure: Exception): VaultRotationFailure = when {
        failure is VaultBiometricFailure -> VaultRotationFailure.BIOMETRIC_UNAVAILABLE
        failure is CancellationException -> VaultRotationFailure.CANCELLED
        failure is VaultException && failure.code == VaultError.AUTHENTICATION_FAILED -> VaultRotationFailure.AUTHENTICATION
        failure is VaultException && failure.code == VaultError.SESSION_CLOSED -> VaultRotationFailure.SESSION_CLOSED
        failure is VaultException && failure.code == VaultError.INVALID_INPUT -> VaultRotationFailure.INVALID_INPUT
        else -> VaultRotationFailure.STORAGE
    }
}
