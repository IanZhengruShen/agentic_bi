/**
 * User and authentication type definitions.
 *
 * These types mirror the backend Pydantic schemas.
 */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  company_id: string | null;
  department: string | null;
  role: 'admin' | 'analyst' | 'viewer' | 'user';
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  department?: string;
  company_name?: string;
}
