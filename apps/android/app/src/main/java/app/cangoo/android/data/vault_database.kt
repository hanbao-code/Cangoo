package app.cangoo.android.data

import android.content.Context
import android.database.Cursor
import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Index
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Update
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import net.zetetic.database.Logger
import net.zetetic.database.NoopTarget
import net.zetetic.database.sqlcipher.SQLiteDatabase
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import java.io.File

@Entity(tableName = "passwords", indices = [Index(value = ["title"], unique = true)])
data class PasswordRecord(
    @PrimaryKey val id: String,
    @ColumnInfo(collate = ColumnInfo.BINARY) val title: String,
    val account: String,
    val password: String,
    val notes: String,
    val updatedAt: String,
    @ColumnInfo(defaultValue = "0") val favorite: Boolean = false,
    @ColumnInfo(defaultValue = "1") val revision: Long = 1,
    val createdAt: String? = null,
    val passwordChangedAt: String? = null,
    @ColumnInfo(defaultValue = "''") val totpSecret: String = "",
    @ColumnInfo(defaultValue = "'[]'") val recoveryCodesJson: String = "[]",
    val strength: String? = null,
    val strengthScheme: String? = null,
) {
    override fun toString() = "PasswordRecord(内容已隐藏)"
}

@Entity(tableName = "notes")
data class NoteRecord(
    @PrimaryKey val id: String,
    @ColumnInfo(collate = ColumnInfo.BINARY) val title: String,
    val content: String,
    val createdAt: String,
    val updatedAt: String,
    @ColumnInfo(defaultValue = "0") val favorite: Boolean = false,
    @ColumnInfo(defaultValue = "1") val revision: Long = 1,
    @ColumnInfo(defaultValue = "0") val sortOrder: Int = 0,
) {
    override fun toString() = "NoteRecord(内容已隐藏)"
}

@Dao
internal interface PasswordDao {
    @Query("SELECT id FROM passwords ORDER BY id LIMIT :limit OFFSET :offset")
    fun backupIds(limit: Int, offset: Int): Cursor

    @Query("SELECT count(*) FROM passwords")
    fun backupCount(): Long

    @Query("SELECT revision FROM passwords WHERE id = :id")
    fun backupRevision(id: String): Long?

    @Query("SELECT length(CAST(title AS BLOB)) + length(CAST(account AS BLOB)) + length(CAST(password AS BLOB)) + length(CAST(notes AS BLOB)) + length(CAST(totpSecret AS BLOB)) + length(CAST(updatedAt AS BLOB)) + COALESCE(length(CAST(passwordChangedAt AS BLOB)), 0) FROM passwords WHERE id = :id")
    fun backupTextBytes(id: String): Long

    @Query("SELECT length(CAST(recoveryCodesJson AS BLOB)) FROM passwords WHERE id = :id")
    fun backupRecoveryBytes(id: String): Long

    @Query("""
        SELECT id, substr(title, 1, 128) AS title, substr(account, 1, 128) AS account,
               updatedAt, favorite, revision, (totpSecret != '') AS hasTotp, 0 AS recoveryCodeCount,
               (length(title) > 128) AS titleTruncated, (length(account) > 128) AS accountTruncated
        FROM passwords ORDER BY updatedAt DESC, id
    """)
    fun list(): List<PasswordSummary>

    @Query("SELECT id, title, account FROM passwords ORDER BY updatedAt DESC, id")
    fun searchValues(): Cursor

    @Query("SELECT id, title, updatedAt FROM passwords")
    fun orderValues(): Cursor

    @Query("SELECT recoveryCodesJson FROM passwords WHERE id = :id")
    fun recoveryJson(id: String): String?

    @Query("SELECT count(*) FROM passwords WHERE password != ''")
    fun checkedCount(): Int

    @Query("SELECT id FROM passwords WHERE password != '' AND strength = 'weak' AND strengthScheme = :scheme")
    fun weakIds(scheme: String): List<String>

    @Query("SELECT id FROM passwords WHERE password != '' AND (strengthScheme IS NULL OR strengthScheme != :scheme OR strength IS NULL OR strength NOT IN ('weak', 'fair', 'strong')) ORDER BY id")
    fun pendingStrengthIds(scheme: String): List<String>

    @Query("SELECT id FROM passwords WHERE title = :title COLLATE BINARY")
    fun idForTitle(title: String): String?

    @Query("UPDATE passwords SET strength = :level, strengthScheme = :scheme WHERE id = :id")
    fun writeStrength(id: String, level: String, scheme: String): Int

    @Query("SELECT id FROM passwords WHERE password != '' AND password IN (SELECT password FROM passwords WHERE password != '' GROUP BY password HAVING count(*) > 1)")
    fun repeatedIds(): List<String>

    @Query("SELECT * FROM passwords WHERE id = :id")
    fun read(id: String): PasswordRecord?

    @Query("SELECT EXISTS(SELECT 1 FROM passwords WHERE title = :title COLLATE BINARY AND id != :exceptId)")
    fun nameExists(title: String, exceptId: String = ""): Boolean

    @Insert
    fun insert(record: PasswordRecord)

    @Update
    fun update(record: PasswordRecord): Int

    @Query("DELETE FROM passwords WHERE id = :id AND revision = :revision")
    fun delete(id: String, revision: Long): Int
}

@Dao
internal interface NoteDao {
    @Query("SELECT id FROM notes ORDER BY id LIMIT :limit OFFSET :offset")
    fun backupIds(limit: Int, offset: Int): Cursor

    @Query("SELECT count(*) FROM notes")
    fun backupCount(): Long

    @Query("SELECT revision FROM notes WHERE id = :id")
    fun backupRevision(id: String): Long?

    @Query("SELECT length(CAST(title AS BLOB)) + length(CAST(content AS BLOB)) + length(CAST(createdAt AS BLOB)) + length(CAST(updatedAt AS BLOB)) FROM notes WHERE id = :id")
    fun backupTextBytes(id: String): Long

    @Query("""
        SELECT id, substr(title, 1, 128) AS title, substr(content, 1, min(128, instr(content || char(10), char(10)) - 1)) AS preview,
               updatedAt, favorite, revision, (length(title) > 128) AS titleTruncated FROM notes ORDER BY updatedAt DESC, id
    """)
    fun list(): List<NoteSummary>

    @Query("SELECT * FROM notes WHERE id = :id")
    fun read(id: String): NoteRecord?

    @Query("SELECT MAX(sortOrder) FROM notes")
    fun lastSortOrder(): Int?

    @Query("SELECT id, title, updatedAt FROM notes")
    fun orderValues(): Cursor

    @Insert
    fun insert(record: NoteRecord)

    @Update
    fun update(record: NoteRecord): Int

    @Query("DELETE FROM notes WHERE id = :id AND revision = :revision")
    fun delete(id: String, revision: Long): Int
}

@Database(entities = [PasswordRecord::class, NoteRecord::class], version = 4, exportSchema = true)
internal abstract class VaultDatabase : RoomDatabase() {
    abstract fun passwords(): PasswordDao
    abstract fun notes(): NoteDao

    companion object {
        private val migration1To2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE passwords ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE passwords ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
                db.execSQL("ALTER TABLE passwords ADD COLUMN createdAt TEXT")
                db.execSQL("ALTER TABLE passwords ADD COLUMN passwordChangedAt TEXT")
                // v1只有新增写入，原更新时间就是该记录的新增与密码录入时间。
                db.execSQL("UPDATE passwords SET createdAt = updatedAt, passwordChangedAt = updatedAt")
                db.execSQL("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id TEXT NOT NULL, title TEXT NOT NULL COLLATE BINARY, content TEXT NOT NULL,
                        createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL,
                        favorite INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1,
                        PRIMARY KEY(id)
                    )
                """)
            }
        }

        private fun migration2To3(guard: (() -> Unit)?) = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                val check = guard ?: throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
                check()
                db.execSQL("ALTER TABLE passwords ADD COLUMN totpSecret TEXT NOT NULL DEFAULT ''")
                db.execSQL("ALTER TABLE passwords ADD COLUMN recoveryCodesJson TEXT NOT NULL DEFAULT '[]'")
                db.execSQL("ALTER TABLE passwords ADD COLUMN strength TEXT")
                db.execSQL("ALTER TABLE notes ADD COLUMN sortOrder INTEGER NOT NULL DEFAULT 0")
                db.query("SELECT id FROM notes ORDER BY updatedAt DESC, id").use { rows ->
                    var order = 0
                    while (rows.moveToNext()) {
                        check()
                        db.execSQL("UPDATE notes SET sortOrder = ? WHERE id = ?", arrayOf(order++, rows.getString(0)))
                    }
                }
                check()
            }
        }

        private fun migration3To4(guard: (() -> Unit)?) = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                val check = guard ?: throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
                check()
                db.execSQL("ALTER TABLE passwords ADD COLUMN strengthScheme TEXT")
                check()
            }
        }

        fun initializeNative() {
            System.loadLibrary("sqlcipher")
            Logger.setTarget(NoopTarget())
            check(SQLiteDatabase.hasCodec())
        }

        fun open(context: Context, file: File, key: ByteArray, create: Boolean = false, migrationGuard: (() -> Unit)? = null): VaultDatabase {
            if (!create && (!file.isFile || file.length() == 0L)) throw VaultException(VaultError.DATA_UNAVAILABLE)
            initializeNative()
            val database = Room.databaseBuilder(context, VaultDatabase::class.java, file.absolutePath)
                .openHelperFactory(SupportOpenHelperFactory(key))
                .setJournalMode(JournalMode.TRUNCATE)
                .addMigrations(migration1To2, migration2To3(migrationGuard), migration3To4(migrationGuard))
                .build()
            try {
                // 强制打开并检查结构；不能把延迟打开当作认证成功。
                database.openHelper.writableDatabase.query("SELECT count(*) FROM passwords").use { it.moveToFirst() }
                return database
            } catch (failure: Exception) {
                database.close()
                throw failure
            }
        }
    }
}
