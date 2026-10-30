import java.security.MessageDigest

plugins {
    id("com.chaquo.python")
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.devtools.ksp")
}

val strengthCore = listOf("core/__init__.py", "core/password_tools.py", "core/i18n.py",
    "core/i18n/zh.json", "core/i18n/en.json", "core/dictionaries/pinyin.txt",
    "core/dictionaries/phrases.txt", "core/dictionaries/leaked_cn.txt")
val strengthRequirements = listOf("zxcvbn==4.5.0", "pypinyin==0.55.0")
val windowsRoot = rootProject.file("../windows")
val checkLegalContent by tasks.registering(Exec::class) {
    description = "检查共同协议与安卓许可生成物，避免打包过期正文"
    val script = rootProject.file("scripts/generate_legal_content.py")
    inputs.file(script)
    inputs.file(windowsRoot.resolve("desktop/frontend/assets/help/content.json"))
    inputs.file("src/main/assets/legal_content.json")
    inputs.files(fileTree("src/main/assets") {
        include("third_party/**", "*_license.txt", "password_strength/licenses/**")
    })
    environment("PYTHONUTF8", "1")
    commandLine(providers.gradleProperty("strengthBuildPython").getOrElse("python"), script, "--check")
}
tasks.named("preBuild") { dependsOn(checkLegalContent) }
val strengthDigest = MessageDigest.getInstance("SHA-256").apply {
    update(strengthRequirements.joinToString("\n").toByteArray(Charsets.UTF_8))
    strengthCore.forEach { name -> update(name.toByteArray(Charsets.UTF_8)); update(windowsRoot.resolve(name).readBytes()) }
}.digest().joinToString("") { "%02x".format(it) }
val syncStrengthCore by tasks.registering(Sync::class) {
    from(windowsRoot) { include(strengthCore) }
    into(layout.buildDirectory.dir("generated/strength/python"))
}
chaquopy {
    defaultConfig {
        version = "3.11"
        providers.gradleProperty("strengthBuildPython").orNull?.let { buildPython(it) }
        pip { strengthRequirements.forEach { install(it) } }
    }
    sourceSets.getByName("main") { srcDir(syncStrengthCore) }
}
tasks.matching { it.name.startsWith("merge") && it.name.endsWith("PythonSources") }.configureEach { dependsOn(syncStrengthCore) }

android {
    namespace = "app.cangoo.android"
    compileSdk = 36
    buildToolsVersion = "36.1.0"

    defaultConfig {
        applicationId = "app.cangoo.android"
        minSdk = 29
        targetSdk = 36
        buildConfigField("String", "STRENGTH_SCHEME", "\"$strengthDigest\"")
        versionCode = 3
        versionName = "1.0.2"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    flavorDimensions += "abi"
    productFlavors {
        create("arm64") { dimension = "abi"; ndk { abiFilters += "arm64-v8a" } }
        create("x64") { dimension = "abi"; ndk { abiFilters += "x86_64" } }
        create("arm32") { dimension = "abi"; ndk { abiFilters += "armeabi-v7a" } }
        create("x86") { dimension = "abi"; ndk { abiFilters += "x86" } }
    }
    buildTypes {
        debug {
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-debug"
            resValue("string", "app_name", "小仓·验收")
        }
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            resValue("string", "app_name", "小仓")
        }
    }
    buildFeatures {
        buildConfig = true
        compose = true
        resValues = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { animationsDisabled = true }
}

kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
ksp { arg("room.schemaLocation", "$projectDir/schemas") }

dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.11.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.9.4")
    implementation("androidx.room:room-runtime:2.8.5")
    implementation("androidx.room:room-ktx:2.8.5")
    ksp("androidx.room:room-compiler:2.8.5")
    implementation("net.zetetic:sqlcipher-android:4.19.1")
    implementation("org.bouncycastle:bcprov-jdk15to18:1.86")
    implementation("com.google.code.gson:gson:2.14.0")
    implementation("com.fasterxml.jackson.core:jackson-core:2.22.3")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.10.2")
}
