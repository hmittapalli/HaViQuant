// Set VITE_API_URL to the deployed API origin at build time.
// Relative URLs support a same-origin reverse proxy in production.
export const API = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '')).replace(/\/$/, '');
