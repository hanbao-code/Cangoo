package app.cangoo.android.data

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.system.Os
import android.system.OsConstants
import android.util.AtomicFile
import app.cangoo.android.data.VaultDescriptorAuth.field
import java.io.ByteArrayInputStream
import java.io.DataInputStream
import java.io.File
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey

internal data class DeletionAsset(val path: String, val device: Long, val inode: Long, val size: Long, val digest: String)
internal data class DeletionReceipt(
    val id: String, val operation: String, val rootDevice: Long, val rootInode: Long,
    val directoryDevice: Long, val directoryInode: Long, val bindings: VaultBindingClaims,
    val assets: List<DeletionAsset>,
) {
    val removedName get() = ".removed_${id}_$operation"
    val receiptName get() = ".deletion_$operation.bin"
}

/** 只签已再次认证并明确确认的删除责任；设备键不能解开任何密码库。 */
internal object VaultDeletionReceipts {
    private const val DOMAIN = "cangoo-android-vault-deletion"
    // 限制不可信责任元数据的读取；超出时在库目录发布前失败。
    private const val MAX_BYTES = 1024 * 1024

    internal fun keyAlias(root: File): String = "cangoo_deletion_" +
        MessageDigest.getInstance("SHA-256").digest(root.absolutePath.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    private fun key(root: File, create: Boolean): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val alias = keyAlias(root)
        val current = store.getKey(alias, null)
        if (current != null) return (current as? SecretKey)?.also { require(it.encoded == null && it.algorithm == "HmacSHA256") }
            ?: unavailable()
        if (!create || store.containsAlias(alias)) unavailable()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_HMAC_SHA256, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                .setKeySize(256).setDigests(KeyProperties.DIGEST_SHA256).setUserAuthenticationRequired(false).build())
            generateKey()
        }
    }

    private fun mac(key: SecretKey, bytes: ByteArray): ByteArray = Mac.getInstance("HmacSHA256").run {
        init(key); doFinal(bytes)
    }

    private fun encode(receipt: DeletionReceipt): ByteArray {
        validate(receipt)
        val size = receipt.assets.sumOf { it.path.toByteArray(Charsets.UTF_8).size.toLong() + it.digest.length + 32 } +
            receipt.bindings.aliases.sumOf { it.length.toLong() + 4 } + 256
        require(size <= MAX_BYTES)
        return VaultDescriptorAuth.encoding(DOMAIN) {
            field(receipt.id); field(receipt.operation)
            writeLong(receipt.rootDevice); writeLong(receipt.rootInode)
            writeLong(receipt.directoryDevice); writeLong(receipt.directoryInode)
            writeBoolean(receipt.bindings.complete)
            writeInt(receipt.bindings.aliases.size); receipt.bindings.aliases.forEach { field(it) }
            writeInt(receipt.assets.size)
            receipt.assets.forEach { entry ->
                field(entry.path); writeLong(entry.device); writeLong(entry.inode); writeLong(entry.size); field(entry.digest)
            }
        }.also { require(it.size + 32 <= MAX_BYTES) }
    }

    private fun validate(receipt: DeletionReceipt) {
        require(VaultDescriptorAuth.validUuid(receipt.id) && VaultDescriptorAuth.validUuid(receipt.operation))
        require(receipt.rootDevice >= 0 && receipt.rootInode > 0 && receipt.directoryDevice >= 0 && receipt.directoryInode > 0)
        require(receipt.bindings.aliases.distinct() == receipt.bindings.aliases)
        require(receipt.bindings.aliases.all { alias -> alias.startsWith("cangoo_vault_${receipt.id}_") &&
            VaultDescriptorAuth.validUuid(alias.removePrefix("cangoo_vault_${receipt.id}_")) })
        require(receipt.assets.map { it.path }.distinct().size == receipt.assets.size)
        require(receipt.assets.singleOrNull { it.path.isEmpty() } ==
            DeletionAsset("", receipt.directoryDevice, receipt.directoryInode, -1, ""))
        val directories = receipt.assets.filter { it.size == -1L }.map { it.path }.toSet()
        receipt.assets.forEach { entry ->
            require(entry.device >= 0 && entry.inode > 0 && entry.size >= -1)
            require(if (entry.size == -1L) entry.digest.isEmpty() else entry.digest.matches(Regex("[0-9a-f]{64}")))
            require(entry.path.isEmpty() || !entry.path.startsWith('/') && '\\' !in entry.path &&
                entry.path.split('/').none { it.isEmpty() || it == "." || it == ".." } &&
                entry.path.substringBeforeLast('/', "") in directories)
        }
    }

    fun write(root: File, receipt: DeletionReceipt) {
        val file = File(root, receipt.receiptName)
        require(parts(file).all { !java.nio.file.Files.exists(it.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS) })
        val payload = encode(receipt)
        val tag = mac(key(root, create = true), payload)
        val bytes = payload + tag
        val atomic = AtomicFile(file)
        var output: java.io.FileOutputStream? = null
        try {
            output = atomic.startWrite()
            checkParts(file)
            val pending = Os.lstat(file.path + ".new")
            require(sameIdentity(pending, Os.fstat(output.fd)))
            output.write(bytes); output.fd.sync()
            require(sameIdentity(pending, Os.lstat(file.path + ".new")))
            atomic.finishWrite(output); output = null
            require(read(root, file) == receipt)
            syncDirectory(root)
        } catch (failure: Exception) {
            output?.let(atomic::failWrite)
            throw failure
        } finally { payload.fill(0); tag.fill(0); bytes.fill(0) }
    }

    fun read(root: File, file: File): DeletionReceipt {
        require(file.parentFile == root && file.name.startsWith(".deletion_") && file.name.endsWith(".bin"))
        checkParts(file)
        // 回执只创建一次；未完成或后来出现的配套文件不能靠AtomicFile读恢复静默删除。
        require(parts(file).drop(1).none { java.nio.file.Files.exists(it.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS) })
        val bytes = file.inputStream().use { input ->
            checkParts(file)
            val before = Os.lstat(file.absolutePath)
            require(OsConstants.S_ISREG(before.st_mode) && before.st_size in 33..MAX_BYTES.toLong() &&
                sameIdentity(before, Os.fstat(input.fd)))
            ByteArray(before.st_size.toInt()).also { buffer ->
                var position = 0
                while (position < buffer.size) {
                    val count = input.read(buffer, position, buffer.size - position)
                    require(count > 0); position += count
                }
                require(input.read() == -1 && sameStamp(before, Os.fstat(input.fd)) && sameStamp(before, Os.lstat(file.absolutePath)))
            }
        }
        try {
            val payload = bytes.copyOfRange(0, bytes.size - 32)
            val tag = bytes.copyOfRange(bytes.size - 32, bytes.size)
            val expected = mac(key(root, create = false), payload)
            try {
                require(MessageDigest.isEqual(tag, expected))
                return DataInputStream(ByteArrayInputStream(payload)).use { input ->
                    fun text(): String {
                        val size = input.readInt(); require(size in 0..4096 && size <= input.available())
                        val value = ByteArray(size).also(input::readFully)
                        return try { value.decodeToString(throwOnInvalidSequence = true) } finally { value.fill(0) }
                    }
                    fun count(): Int = input.readInt().also { require(it in 0..input.available() / 4) }
                    require(text() == DOMAIN && input.readInt() == 1)
                    val id = text(); val operation = text()
                    val rootDevice = input.readLong(); val rootInode = input.readLong()
                    val device = input.readLong(); val inode = input.readLong()
                    val complete = input.readUnsignedByte().also { require(it in 0..1) } == 1
                    val aliases = List(count()) { text() }
                    val assets = List(count()) { DeletionAsset(text(), input.readLong(), input.readLong(), input.readLong(), text()) }
                    require(input.available() == 0)
                    DeletionReceipt(id, operation, rootDevice, rootInode, device, inode, VaultBindingClaims(aliases, complete), assets)
                        .also { validate(it); require(it.receiptName == file.name) }
                }
            } finally { payload.fill(0); tag.fill(0); expected.fill(0) }
        } finally { bytes.fill(0) }
    }

    fun remove(root: File, receipt: DeletionReceipt) {
        val file = File(root, receipt.receiptName)
        val before = Os.lstat(file.absolutePath)
        require(read(root, file) == receipt && sameStamp(before, Os.lstat(file.absolutePath)))
        Os.remove(file.absolutePath); syncDirectory(root)
    }

    private fun parts(file: File) = listOf(file, File(file.path + ".bak"), File(file.path + ".new"))
    private fun checkParts(file: File) {
        require(file.parentFile!!.canonicalFile == file.parentFile!!.absoluteFile)
        parts(file).forEach { part ->
            require(part.canonicalFile == part.absoluteFile && !java.nio.file.Files.isSymbolicLink(part.toPath()))
            if (java.nio.file.Files.exists(part.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS))
                require(OsConstants.S_ISREG(Os.lstat(part.absolutePath).st_mode))
        }
    }
    private fun sameIdentity(a: android.system.StructStat, b: android.system.StructStat) = a.st_dev == b.st_dev && a.st_ino == b.st_ino
    private fun sameStamp(a: android.system.StructStat, b: android.system.StructStat) = sameIdentity(a, b) && a.st_size == b.st_size &&
        a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
        a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
    private fun unavailable(): Nothing = throw VaultException(VaultError.DATA_UNAVAILABLE)
}
