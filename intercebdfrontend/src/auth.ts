import { ref, computed } from 'vue';
import axios from 'axios';
import { API_BASE_URL } from './config';

interface UserInfo {
  sub: string;
  email?: string;
  name?: string | null;
}

const user = ref<UserInfo | null>(null);
const isLoading = ref<boolean>(true);

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value);
 
  async function checkLoginStatus() {
    isLoading.value = true;
    try {
      const response = await axios.get<{ is_logged_in: Boolean; user_info: UserInfo | null}>(
        `${API_BASE_URL}/auth/login_status`,
        { withCredentials: true }
      )
      
      if (response.data.is_logged_in && response.data.user_info) {
        user.value = response.data.user_info;
      }
      else {
        user.value = null;
      }
    } catch (error) {
      console.error("Error checking login status:", error);
      user.value = null; // Assume logged out on error
    } finally {
      isLoading.value = false;
    }
  }

  function logout() {
    window.location.href = `${API_BASE_URL}/auth/logout`;
    user.value = null;
  }

  function login() {
    window.location.href = `${API_BASE_URL}/auth/login/google`;
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    checkLoginStatus,
    logout,
    login
  }
}