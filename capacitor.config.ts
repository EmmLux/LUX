import type { CapacitorConfig } from "@capacitor/cli";

const deploymentUrl = process.env.LUX_WEB_URL;

if (!deploymentUrl) {
  throw new Error(
    "LUX_WEB_URL es obligatoria y debe ser la URL HTTPS pública del backend Django de Lux."
  );
}

const url = new URL(deploymentUrl);
if (url.protocol !== "https:") {
  throw new Error("LUX_WEB_URL debe usar HTTPS; Google Play no admite tráfico HTTP en producción.");
}

const config: CapacitorConfig = {
  appId: "com.emmlux.app",
  appName: "Lux",
  webDir: "mobile/www",
  server: {
    url: url.toString(),
    cleartext: false,
    allowNavigation: [url.host]
  },
  android: {
    allowMixedContent: false,
    backgroundColor: "#030405"
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      launchAutoHide: true,
      backgroundColor: "#030405",
      androidScaleType: "CENTER_CROP",
      showSpinner: false
    }
  }
};

export default config;
