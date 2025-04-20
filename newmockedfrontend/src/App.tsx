import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProjectHomePage from "./pages/ProjectHomePage";
import CallerPage from "./pages/CallerPage";
import JsonSchemaPage from "./pages/JsonSchemaPage";
import GenerateDatasetPage from "./pages/GenerateDatasetPage";
import RequestDetailsPage from "./pages/RequestDetailsPage";
import LoadingSpinner from "@/components/LoadingSpinner"; // Import the new component

// Define types for API responses (match your backend Pydantic models)
interface UserInfo {
  id: string;
  email?: string | null;
  google_id?: string | null;
  auth_provider?: string | null;
  name?: string | null;
}

interface LoginStatusResponse {
  is_logged_in: boolean;
  is_guest: boolean;
  user_info: UserInfo | null;
}

interface DefaultProjectResponse {
  project: {
    id: string;
  };
  key?: {
    id: string;
    key: string;
  } | null;
}

interface GuestUserResponse {
  guest_user_id: string; // UUID comes as string in JSON
}

// Get the base URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""; // Fallback to empty string if not set

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    const initializeUserAndProject = async () => {
      setIsLoading(true);
      const storedGuestId = localStorage.getItem('guestUserId'); // Check localStorage
      console.log("Initial check: localStorage guestUserId =", storedGuestId);

      try {
        // 1. Check backend login status (always includes credentials)
        const statusResponse = await fetch(`${API_BASE_URL}/auth/login_status`, { credentials: 'include' });
        if (!statusResponse.ok) {
          // Handle network or server errors for login status check
          if (statusResponse.status === 401) {
             console.warn("Login status check returned 401, proceeding as unauthenticated.");
             // Treat as not logged in, let logic below handle guest/new visitor
          } else {
            throw new Error(`Login status check failed: ${statusResponse.status} ${statusResponse.statusText}`);
          }
        }

        // Process status only if response was okay or a handled error like 401
        const statusData: LoginStatusResponse = statusResponse.ok ? await statusResponse.json() : { is_logged_in: false, is_guest: false, user_info: null };

        let effectiveUserId: string | null = null;
        let projectFetchNeeded = true; // Flag to control project fetching

        if (statusData.is_logged_in && statusData.user_info) {
          // --- Scenario 1: User is properly logged in ---
          console.log("Backend confirms: User is logged in:", statusData.user_info);
          effectiveUserId = statusData.user_info.id;
          localStorage.removeItem('guestUserId'); // Clear any old guest ID

          // Fetch default project using cookie auth
          console.log("Fetching default project for logged-in user...");
          const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, { method: "POST", credentials: 'include' });
          if (!projectResponse.ok) throw new Error(`Failed project fetch for logged-in user: ${projectResponse.statusText}`);
          const projectData: DefaultProjectResponse = await projectResponse.json();
          setProjectId(projectData.project.id);
          projectFetchNeeded = false; // Project already fetched

        } else if (statusData.is_guest && statusData.user_info) {
          // --- Scenario 2: Backend recognizes guest via cookie ---
          console.log("Backend confirms: User is guest (via cookie):", statusData.user_info);
          effectiveUserId = statusData.user_info.id;
          // Ensure localStorage is up-to-date
          if (localStorage.getItem('guestUserId') !== effectiveUserId) {
             localStorage.setItem('guestUserId', effectiveUserId);
             console.log("Updated localStorage with guest ID from cookie.");
          }

          // Fetch default project using cookie auth
          console.log("Fetching default project for guest user (cookie)...");
          const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, { method: "POST", credentials: 'include' });
           if (!projectResponse.ok) throw new Error(`Failed project fetch for guest user: ${projectResponse.statusText}`);
          const projectData: DefaultProjectResponse = await projectResponse.json();
          setProjectId(projectData.project.id);
          projectFetchNeeded = false; // Project already fetched

        } else {
          // --- Scenario 3: Backend sees no active session (not logged in, no valid guest cookie received) ---
          console.log("Backend sees no active session.");

          if (storedGuestId) {
            // --- Sub-Scenario 3a: Try using guest ID from localStorage ---
            console.log("Attempting to use guest ID from localStorage:", storedGuestId);
            effectiveUserId = storedGuestId;

            try {
              const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: effectiveUserId }), // Use stored ID
                credentials: 'include' // Keep sending credentials
              });

              if (projectResponse.ok) {
                console.log("Successfully used localStorage guest ID to get/create project.");
                const projectData: DefaultProjectResponse = await projectResponse.json();
                setProjectId(projectData.project.id);
                projectFetchNeeded = false; // Project fetched/found
              } else {
                 console.warn(`Failed to use localStorage guest ID ${effectiveUserId} (Status: ${projectResponse.status}). Clearing localStorage.`);
                 localStorage.removeItem('guestUserId');
                 effectiveUserId = null; // Invalidate ID, will trigger new guest creation below
              }
            } catch (localIdError) {
               console.error("Error trying to use localStorage guest ID:", localIdError);
               localStorage.removeItem('guestUserId');
               effectiveUserId = null; // Invalidate ID, will trigger new guest creation below
            }
          }

          // --- Sub-Scenario 3b: Create a new guest if needed ---
          if (!effectiveUserId && projectFetchNeeded) { // Only create if no ID worked and project still needed
            console.log("Creating new guest user...");
            const guestResponse = await fetch(`${API_BASE_URL}/auth/users/guest`, { method: "POST" });
            if (!guestResponse.ok) throw new Error(`Failed to create guest user: ${guestResponse.statusText}`);

            const guestData: GuestUserResponse = await guestResponse.json();
            effectiveUserId = guestData.guest_user_id;
            console.log("New guest user created:", effectiveUserId);
            localStorage.setItem('guestUserId', effectiveUserId); // Store new ID

            console.log("Creating default project for new guest...");
            const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, {
              method: "POST",
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: effectiveUserId }), // Use the new ID
              credentials: 'include'
            });
            if (!projectResponse.ok) throw new Error(`Failed project fetch for new guest: ${projectResponse.statusText}`);
            const projectData: DefaultProjectResponse = await projectResponse.json();
            setProjectId(projectData.project.id);
            projectFetchNeeded = false; // Project created
          }
        }

        // Final check if a project ID was determined
        if (!projectId && projectFetchNeeded) { // Check if projectId was set in any path
           throw new Error("Failed to determine a project ID after all checks.");
        }

      } catch (error) {
        console.error("Initialization failed:", error);
        // Consider clearing local storage on critical failure?
        // localStorage.removeItem('guestUserId');
      } finally {
        setIsLoading(false);
      }
    };

    initializeUserAndProject();
  }, [projectId]); // Re-run if projectId changes (might not be needed, depends on desired behavior)

  if (isLoading) {
    return <LoadingSpinner />; // Use the new component
  }

  if (!projectId) {
      // Also check if API_BASE_URL was missing
      if (!API_BASE_URL) {
          return <div>Error: API Base URL is not configured. Please check the environment variables.</div>;
      }
      return <div>Error: Could not initialize project. Please try refreshing.</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to={`/${projectId}`} replace />} />
        <Route path="/" element={<Layout />}>
          <Route path=":projectId" element={<ProjectHomePage />} />
          <Route path=":projectId/caller" element={<CallerPage />} />
          <Route path=":projectId/json-schema" element={<JsonSchemaPage />} />
          <Route path=":projectId/generate-dataset" element={<GenerateDatasetPage />} />
          <Route path=":projectId/requests/:requestId" element={<RequestDetailsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;