import { useState, useEffect } from "react";
// *** Import useNavigate ***
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProjectHomePage from "./pages/ProjectHomePage";
import CallerPage from "./pages/CallerPage";
import JsonSchemaPage from "./pages/JsonSchemaPage";
import GenerateDatasetPage from "./pages/GenerateDatasetPage";
import RequestDetailsPage from "./pages/RequestDetailsPage";
import LoadingSpinner from "@/components/LoadingSpinner";
import { LoginStatusResponse, DefaultProjectResponse, GuestUserResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const GUEST_USER_ID_HEADER = "X-Guest-User-Id"; // Define header name constant

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [userStatus, setUserStatus] = useState<LoginStatusResponse | null>(null);
  const [initializationError, setInitializationError] = useState<string | null>(null); // State for error message

  // --- Initialization Effect ---
  useEffect(() => {
    let isMounted = true; // Flag to prevent state updates on unmounted component
    const initializeUserAndProject = async () => {
      console.log("Starting initialization..."); // Add log
      setIsLoading(true);
      setInitializationError(null); // Clear previous errors
      setUserStatus(null);
      const storedGuestId = localStorage.getItem('guestUserId');
      console.log("Initial check: localStorage guestUserId =", storedGuestId);

      try {
        // 1. Check backend login status
        const statusResponse = await fetch(`${API_BASE_URL}/auth/login_status`, { credentials: 'include' });
        const statusData: LoginStatusResponse = statusResponse.ok ? await statusResponse.json() : { is_logged_in: false, is_guest: false, user_info: null };
        if (isMounted) setUserStatus(statusData);

        let effectiveUserId: string | null = null;
        let fetchedProjectId: string | null = null; // Temporary variable to hold ID

        if (statusData.is_logged_in && statusData.user_info) {
          // --- Scenario 1: Logged In ---
          console.log("Backend confirms: User is logged in:", statusData.user_info);
          effectiveUserId = statusData.user_info.id;
          localStorage.removeItem('guestUserId');
          console.log("Fetching default project for logged-in user...");
          const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, { method: "POST", credentials: 'include' });
          if (!projectResponse.ok) throw new Error(`Failed project fetch for logged-in user: ${projectResponse.statusText}`);
          const projectData: DefaultProjectResponse = await projectResponse.json();
          fetchedProjectId = projectData.project.id; // Store in temp variable

        } else if (statusData.is_guest && statusData.user_info) {
          // --- Scenario 2: Guest (Cookie) ---
          console.log("Backend confirms: User is guest (via cookie):", statusData.user_info);
          effectiveUserId = statusData.user_info.id;
          if (localStorage.getItem('guestUserId') !== effectiveUserId) {
             localStorage.setItem('guestUserId', effectiveUserId);
             console.log("Updated localStorage with guest ID from cookie.");
          }
          console.log("Fetching default project for guest user (cookie)...");
          const projectResponse = await fetch(`${API_BASE_URL}/completion-projects/default`, { method: "POST", credentials: 'include' });
           if (!projectResponse.ok) throw new Error(`Failed project fetch for guest user: ${projectResponse.statusText}`);
          const projectData: DefaultProjectResponse = await projectResponse.json();
          fetchedProjectId = projectData.project.id; // Store in temp variable

        } else {
          // --- Scenario 3: No Session ---
          console.log("Backend sees no active session.");
          if (storedGuestId) {
            // --- Sub-Scenario 3a: Try localStorage ID ---
            console.log("Attempting to use guest ID from localStorage:", storedGuestId);
            effectiveUserId = storedGuestId;
            try {
              const fetchUrl3a = `${API_BASE_URL}/completion-projects/default`;
              const headers3a: HeadersInit = {
                  'Content-Type': 'application/json',
                  [GUEST_USER_ID_HEADER]: effectiveUserId
              };
              const fetchOptions3a: RequestInit = {
                  method: "POST",
                  headers: headers3a
              };
              console.log(`DEBUG: About to fetch URL (3a): ${fetchUrl3a}`);
              console.log("DEBUG: Fetch options (3a):", JSON.stringify(fetchOptions3a, null, 2));

              const projectResponse = await fetch(fetchUrl3a, fetchOptions3a);

              if (projectResponse.ok) {
                console.log("Successfully used localStorage guest ID (via header) to get/create project.");
                const projectData: DefaultProjectResponse = await projectResponse.json();
                fetchedProjectId = projectData.project.id;
                const newStatusResponse = await fetch(`${API_BASE_URL}/auth/login_status`, { credentials: 'include' });
                const newStatusData = newStatusResponse.ok ? await newStatusResponse.json() : statusData;
                if (isMounted) setUserStatus(newStatusData);

              } else {
                 console.warn(`Failed to use localStorage guest ID ${effectiveUserId} via header (Status: ${projectResponse.status}). Clearing localStorage.`);
                 localStorage.removeItem('guestUserId');
                 effectiveUserId = null; // Invalidate ID to trigger new guest creation
              }
            } catch (localIdError) {
               console.error("Error trying to use localStorage guest ID via header:", localIdError);
               localStorage.removeItem('guestUserId');
               effectiveUserId = null; // Invalidate ID to trigger new guest creation
            }
          }

          // --- Sub-Scenario 3b: Create New Guest ---
          if (!effectiveUserId && !fetchedProjectId) {  
            console.log("Creating new guest user...");
            const guestResponse = await fetch(`${API_BASE_URL}/auth/users/guest`, { method: "POST", credentials: 'include' });
            if (!guestResponse.ok) throw new Error(`Failed to create guest user: ${guestResponse.statusText}`);
            const guestData: GuestUserResponse = await guestResponse.json();
            effectiveUserId = guestData.guest_user_id;
            console.log("New guest user created:", effectiveUserId);
            localStorage.setItem('guestUserId', effectiveUserId);

            console.log("Creating default project for new guest...");

            const fetchUrl = `${API_BASE_URL}/completion-projects/default`;
            const fetchOptions: RequestInit = {
              method: "POST",
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include'
            };
            console.log(`DEBUG: About to fetch URL (3b): ${fetchUrl}`);
            console.log("DEBUG: Fetch options (3b):", JSON.stringify(fetchOptions, null, 2));

            try {
                const projectResponse = await fetch(fetchUrl, fetchOptions);
                if (!projectResponse.ok) {
                    const errorText = await projectResponse.text();
                    console.error(`DEBUG: Project fetch failed (3b) with status ${projectResponse.status}. Response: ${errorText}`);
                    throw new Error(`Failed project fetch for new guest: ${projectResponse.status} ${projectResponse.statusText}`);
                }
                const projectData: DefaultProjectResponse = await projectResponse.json();
                console.log("Received project data (3b):", JSON.stringify(projectData, null, 2));
                if (!projectData?.project?.id) throw new Error("Project ID missing in response (3b).");
                fetchedProjectId = projectData.project.id;
                const finalStatusResponse = await fetch(`${API_BASE_URL}/auth/login_status`, { credentials: 'include' });
                const finalStatusData = finalStatusResponse.ok ? await finalStatusResponse.json() : statusData;
                if (isMounted) setUserStatus(finalStatusData);

            } catch (fetchError) {
                 console.error("DEBUG: Error during project fetch (3b):", fetchError);
                 throw fetchError;
            }
          }
        }

        // --- Set State After All Logic ---
        if (isMounted) {
            if (fetchedProjectId) {
                console.log(`Initialization successful. Setting projectId: ${fetchedProjectId}`);
                setProjectId(fetchedProjectId);
            } else {
                console.error("Initialization completed but no project ID was determined.");
                setInitializationError("Could not determine project ID.");
            }
        }

      } catch (error: any) {
        console.error("Initialization failed:", error);
        if (isMounted) setInitializationError(error.message || "An unknown error occurred during initialization.");
      } finally {
        if (isMounted) {
            console.log("Setting isLoading to false.");
            setIsLoading(false);
        }
      }
    };

    initializeUserAndProject();

    return () => {
        console.log("Initialization effect cleanup."); // Add log
        isMounted = false;
    };
  }, []); // Empty dependency array: Run only once on mount

  // --- Navigation Effect ---
  const navigate = useNavigate();
  useEffect(() => {
    if (projectId) {
      console.log(`Project ID set to ${projectId}, navigating to root project path.`);
      if (!window.location.pathname.includes(projectId)) {
         navigate(`/${projectId}`, { replace: true });
      }
    }
  }, [projectId, navigate]);

  // --- Render Logic ---
  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (initializationError) {
      return <div>Error: {initializationError} Please try refreshing.</div>;
  }

  if (!projectId) {
      console.log("Render: Waiting for projectId to be set...");
      return <LoadingSpinner />;
  }

  console.log(`Render: ProjectId is ${projectId}, rendering Routes.`);
  return (
      <Routes>
        <Route path="/" element={<Layout userStatus={userStatus} />}>
          <Route path=":projectId" element={<ProjectHomePage />} />
          <Route path=":projectId/caller" element={<CallerPage />} />
          <Route path=":projectId/json-schema" element={<JsonSchemaPage />} />
          <Route path=":projectId/generate-dataset" element={<GenerateDatasetPage />} />
          <Route path=":projectId/requests/:requestId" element={<RequestDetailsPage />} />
           <Route index element={<Navigate to={`/${projectId}`} replace />} />
        </Route>
         <Route path="*" element={<Navigate to={`/${projectId}`} replace />} />
      </Routes>
  );
}

// Wrap App with BrowserRouter
function WrappedApp() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}

export default WrappedApp; // Export the wrapped component