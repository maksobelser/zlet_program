// src/utils/auth.js
export function saveToken(jwt) {
    localStorage.setItem('token', jwt);
  }
  
  export function getToken() {
    return localStorage.getItem('token');
  }
  
  export function logout() {
    localStorage.removeItem('token');
  }