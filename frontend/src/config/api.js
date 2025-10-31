// API configuration
const getApiUrl = () => {
  // In production, use the current hostname with port 5050
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:5050`;
  }
  
  // In development, use relative paths (Vite proxy handles it)
  return '';
};

export const API_BASE_URL = getApiUrl();

export const getApiEndpoint = (path) => {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};
