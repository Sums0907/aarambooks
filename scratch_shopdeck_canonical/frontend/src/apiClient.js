const API_BASE_URL = window.AARAM_CONFIG?.API_URL || import.meta.env.VITE_API_URL || "http://localhost:8200/api/v1";

function getIdentityApiUrl() {
  return (
    window.AARAM_CONFIG?.IDENTITY_API_URL ||
    window.AARAM_CONFIG?.IDENTITY_URL ||
    import.meta.env.VITE_IDENTITY_API_URL || 
    "http://127.0.0.1:9000"
  ).replace(/\/$/, "");
}

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

export async function fetchWithAuth(endpoint, options = {}) {
  const endpointStr = endpoint.toString();
  const url = endpointStr.startsWith('http') ? endpointStr : `${API_BASE_URL}${endpointStr}`;
  
  let token = localStorage.getItem('aaram_identity_token');
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const config = { ...options, headers };

  let response = await fetch(url, config);

  if (response.status === 401 && !options._retry) {
    const refreshToken = localStorage.getItem('aaram_refresh_token');

    if (!refreshToken) {
      localStorage.removeItem('aaram_identity_token');
      localStorage.removeItem('aaram_refresh_token');
      localStorage.removeItem('aaram_cached_user');
      window.location.href = '/';
      return response;
    }

    if (!isRefreshing) {
      isRefreshing = true;

      try {
        const refreshUrl = `${getIdentityApiUrl()}/auth/refresh`;
        const refreshRes = await fetch(refreshUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            refresh_token: refreshToken,
            platform: 'SHOPDECK_WEB'
          })
        });

        if (!refreshRes.ok) {
          throw new Error('Refresh failed');
        }

        const data = await refreshRes.json();
        const payload = data.data || data;

        if (payload.access_token) {
          localStorage.setItem('aaram_identity_token', payload.access_token);
          localStorage.setItem('aaram_refresh_token', payload.refresh_token);
          
          isRefreshing = false;
          onRefreshed(payload.access_token);
          
          config.headers.set('Authorization', `Bearer ${payload.access_token}`);
          config._retry = true;
          return await fetch(url, config);
        } else {
          throw new Error("No tokens in response");
        }
      } catch (error) {
        isRefreshing = false;
        localStorage.removeItem('aaram_identity_token');
        localStorage.removeItem('aaram_refresh_token');
        localStorage.removeItem('aaram_cached_user');
        window.location.href = '/';
        return response;
      }
    } else {
      return new Promise(resolve => {
        subscribeTokenRefresh(newToken => {
          config.headers.set('Authorization', `Bearer ${newToken}`);
          config._retry = true;
          resolve(fetch(url, config));
        });
      });
    }
  }

  return response;
}
