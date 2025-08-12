// src/api.js
import axios from 'axios';
import { logout } from './utils/auth';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

// attach JWT on each request if present
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// catch 401s (token expired / invalid) and redirect
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // remove any stale token
      logout();
      // redirect to login page
      // if you’re using react-router v6:
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export default api;