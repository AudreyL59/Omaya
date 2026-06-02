const API_BASE = '/api';

export interface LoginRequest {
  email: string;
  password: string;
  intranet: string;
}

export interface UserToken {
  id_salarie: number;
  login: string;
  nom: string;
  prenom: string;
  is_actif: boolean;
  is_pause: boolean;
  agenda_actif: boolean;
  active_log: boolean;
  gsm: string;
  id_ste: number;
  prof_poste: string;
  droits: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserToken;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Erreur de connexion');
  }

  return res.json();
}

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string) {
  localStorage.setItem('token', token);
}

export function removeToken() {
  localStorage.removeItem('token');
}

export function getStoredUser(): UserToken | null {
  const raw = localStorage.getItem('user');
  return raw ? JSON.parse(raw) : null;
}

export function setStoredUser(user: UserToken) {
  localStorage.setItem('user', JSON.stringify(user));
}

export function removeStoredUser() {
  localStorage.removeItem('user');
}
