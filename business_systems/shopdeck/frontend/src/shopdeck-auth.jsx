import React, { useState, useEffect, createContext, useContext } from 'react';

const AuthContext = createContext(null);

function decodeJWTPayload(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

function buildUserFromPayload(payload) {
  return {
    user_id: payload.sub || "",
    name: payload.name || payload.username || "",
    permissions: payload.permissions || [],
    applications: payload.applications || [],
    roles: payload.roles || [],
    isAuthenticated: true,
  };
}

function getInitialAuthState() {
  if (typeof window !== 'undefined') {
    // Intercept SSO tokens from URL
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    const urlRefreshToken = params.get('refresh_token');
    if (urlToken) {
      localStorage.setItem('aaram_identity_token', urlToken);
      if (urlRefreshToken) {
        localStorage.setItem('aaram_refresh_token', urlRefreshToken);
      }
      // Clean up the URL to remove the tokens to prevent exposure
      const newUrl = window.location.pathname + window.location.hash;
      window.history.replaceState({}, document.title, newUrl);
    }

    const token = localStorage.getItem('aaram_identity_token');
    const refreshToken = localStorage.getItem('aaram_refresh_token');

    if (token) {
      const payload = decodeJWTPayload(token);
      if (payload && payload.exp * 1000 > Date.now()) {
        return buildUserFromPayload(payload);
      }
      localStorage.removeItem('aaram_identity_token');
    }

    if (refreshToken) {
      const refreshPayload = decodeJWTPayload(refreshToken);
      if (refreshPayload && refreshPayload.exp * 1000 > Date.now()) {
        const cachedUser = localStorage.getItem('aaram_cached_user');
        if (cachedUser) {
          try {
            return { ...JSON.parse(cachedUser), isAuthenticated: true };
          } catch (e) {}
        }
      } else {
        localStorage.removeItem('aaram_refresh_token');
      }
    }
  }
  
  return {
    user_id: "",
    name: "",
    permissions: [],
    applications: [],
    roles: [],
    isAuthenticated: false,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getInitialAuthState);

  useEffect(() => {
    if (user.isAuthenticated) {
      localStorage.setItem('aaram_cached_user', JSON.stringify({
        user_id: user.user_id,
        name: user.name,
        permissions: user.permissions,
        applications: user.applications,
        roles: user.roles,
      }));
    }
  }, [user]);

  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'aaram_identity_token' && e.newValue) {
        const payload = decodeJWTPayload(e.newValue);
        if (payload && payload.exp * 1000 > Date.now()) {
          setUser(buildUserFromPayload(payload));
        }
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const value = {
    user,
    hasPermission: (permission) => user.permissions.includes(permission),
    isAuthenticated: user.isAuthenticated,
    logout: () => {
      localStorage.removeItem('aaram_identity_token');
      localStorage.removeItem('aaram_refresh_token');
      localStorage.removeItem('aaram_cached_user');
      window.location.href = '/';
    }
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
