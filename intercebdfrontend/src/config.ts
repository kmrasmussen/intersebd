export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  console.error("Error: VITE_API_BASE_URL is not defined. Check your .env files or DigitalOcean build settings.");
  throw new Error("VITE_API_BASE_URL is not defined");
}