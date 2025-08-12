// src/components/PrivateRoute.js
import { Navigate } from 'react-router-dom';
import { getToken } from '../utils/auth';

export default function PrivateRoute({ children }) {
  return getToken() ? children : <Navigate to="/" replace />;
}