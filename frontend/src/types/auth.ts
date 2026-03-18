export interface AuthUser {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  rol: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  usuario: AuthUser | null;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}
