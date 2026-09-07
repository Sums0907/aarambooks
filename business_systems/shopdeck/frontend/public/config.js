const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
window.AARAM_CONFIG = {
    API_URL: isLocalhost ? "http://127.0.0.1:8200/api/v1" : "https://api-shopdeck.aarambooks.cloud/api/v1",
    IDENTITY_URL: isLocalhost ? "http://127.0.0.1:9001" : "https://identity.aarambooks.cloud",
    IDENTITY_API_URL: isLocalhost ? "http://127.0.0.1:9000" : "https://api-identity.aarambooks.cloud"
};
