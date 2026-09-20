export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  oauth_provider?: string;
  oauth_id?: string;
}

export interface Device {
  id: string;
  session_id: string;
  user_agent?: string;
  browser?: string;
  operating_system?: string;
  ip_address?: string;
  geographic_location?: string;
  last_active_at: string;
}

export interface UserSession {
  id: string;
  user_id: string;
  workspace_id?: string;
  expires_at: string;
  created_at: string;
  device?: Device;
}

export interface TokenResponse {
  access_token: string;
}
