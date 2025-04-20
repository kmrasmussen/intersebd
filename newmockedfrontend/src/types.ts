// User information structure
export interface UserInfo {
  id: string;
  email?: string | null;
  google_id?: string | null;
  auth_provider?: string | null;
  name?: string | null;
}

// Response from /auth/login_status
export interface LoginStatusResponse {
  is_logged_in: boolean;
  is_guest: boolean;
  user_info: UserInfo | null;
}

// Response from /completion-projects/default
export interface DefaultProjectResponse {
  project: {
    id: string;
    // Add other project fields if needed
  };
  key?: {
    id: string;
    key: string;
    // Add other key fields if needed
  } | null;
}

// Response from /auth/users/guest
export interface GuestUserResponse {
  guest_user_id: string;
}

// Add any other shared types here