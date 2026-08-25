import { readFile, writeFile } from "node:fs/promises";

const gradlePath = new URL("../android/app/build.gradle", import.meta.url);
let gradle = await readFile(gradlePath, "utf8");

gradle = gradle
  .replace("compileSdk rootProject.ext.compileSdkVersion", "compileSdk 36")
  .replace("minSdk rootProject.ext.minSdkVersion", "minSdk 23")
  .replace("targetSdk rootProject.ext.targetSdkVersion", "targetSdk 36");

if (!gradle.includes("LUX_UPLOAD_STORE_FILE")) {
  const signing = `
    signingConfigs {
        release {
            def storeFilePath = System.getenv("LUX_UPLOAD_STORE_FILE")
            if (storeFilePath) {
                storeFile file(storeFilePath)
                storePassword System.getenv("LUX_UPLOAD_STORE_PASSWORD")
                keyAlias System.getenv("LUX_UPLOAD_KEY_ALIAS")
                keyPassword System.getenv("LUX_UPLOAD_KEY_PASSWORD")
            }
        }
    }
`;
  gradle = gradle.replace("    buildTypes {", `${signing}\n    buildTypes {`);
  gradle = gradle.replace(
    /release\s*\{[\s\S]*?signingConfig signingConfigs\.debug/,
    "release {\n            if (!System.getenv(\"LUX_UPLOAD_STORE_FILE\")) {\n                throw new GradleException(\"Define LUX_UPLOAD_STORE_FILE y sus credenciales para firmar el bundle de release.\")\n            }\n            signingConfig signingConfigs.release"
  );
}

if (!gradle.includes("compileSdk 36") || !gradle.includes("targetSdk 36") || !gradle.includes("signingConfigs.release")) {
  throw new Error("La plantilla de Capacitor cambió; revisa android/app/build.gradle antes de compilar.");
}

await writeFile(gradlePath, gradle);
console.log("Android configurado: API 36, minSdk 23 y firma de release mediante variables LUX_UPLOAD_*.");
