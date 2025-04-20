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
        // ... status check error handling ...
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
              const fetchOptions3a: RequestInit = {
                  method: "POST",
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ user_id: effectiveUserId }),
                  credentials: 'include'
              };
              const projectResponse = await fetch(fetchUrl3a, fetchOptions3a);

              if (projectResponse.ok) {
                console.log("Successfully used localStorage guest ID to get/create project.");
                const projectData: DefaultProjectResponse = await projectResponse.json();
                fetchedProjectId = projectData.project.id; // Store in temp variable
              } else {
                 // Log the specific error status before clearing
                 console.warn(`Failed to use localStorage guest ID ${effectiveUserId} (Status: ${projectResponse.status}). Clearing localStorage.`);
                 localStorage.removeItem('guestUserId');
                 effectiveUserId = null; // Invalidate ID to trigger new guest creation
              }
            } catch (localIdError) {
               console.error("Error trying to use localStorage guest ID:", localIdError); // Log the actual error
               localStorage.removeItem('guestUserId');
               effectiveUserId = null; // Invalidate ID to trigger new guest creation
            }
          }

          // --- Sub-Scenario 3b: Create New Guest ---
          if (!effectiveUserId && !fetchedProjectId) {  
            console.log("Creating new guest user...");
            const guestResponse = await fetch(`${API_BASE_URL}/auth/users/guest`, { method: "POST" });
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
              body: JSON.stringify({ user_id: effectiveUserId }),
              credentials: 'include'
            };
            console.log(`DEBUG: About to fetch URL: ${fetchUrl}`);
            console.log("DEBUG: Fetch options:", JSON.stringify(fetchOptions, null, 2));

            try {
                const projectResponse = await fetch(fetchUrl, fetchOptions);
                if (!projectResponse.ok) {
                    // Log error details if fetch fails
                    const errorText = await projectResponse.text();
                    console.error(`DEBUG: Project fetch failed with status ${projectResponse.status}. Response: ${errorText}`);
                    throw new Error(`Failed project fetch for new guest: ${projectResponse.status} ${projectResponse.statusText}`);
                }
                const projectData: DefaultProjectResponse = await projectResponse.json();
                console.log("Received project data:", JSON.stringify(projectData, null, 2));
                if (!projectData?.project?.id) throw new Error("Project ID missing in response.");
                fetchedProjectId = projectData.project.id;
            } catch (fetchError) {
                 // Log the specific fetch error
                 console.error("DEBUG: Error during project fetch:", fetchError);
                 throw fetchError; // Re-throw the error to be caught by the outer catch block
            }
          }
        }

        // --- Set State After All Logic ---
        if (isMounted) {
            if (fetchedProjectId) {
                console.log(`Initialization successful. Setting projectId: ${fetchedProjectId}`);
                setProjectId(fetchedProjectId);
            } else {
                // If we reached here without a project ID, something went wrong
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

    // Cleanup function to prevent state updates if component unmounts
    return () => {
        console.log("Initialization effect cleanup."); // Add log
        isMounted = false;
    };
  }, []); // Empty dependency array: Run only once on mount

  // --- Navigation Effect ---
  // This effect runs whenever projectId changes *after* the initial render
  const navigate = useNavigate();
  useEffect(() => {
    if (projectId) {
      console.log(`Project ID set to ${projectId}, navigating to root project path.`);
      // Check if we are already at a project path to avoid loop
      if (!window.location.pathname.includes(projectId)) {
         navigate(`/${projectId}`, { replace: true });
      }
    }
  }, [projectId, navigate]); // Run when projectId or navigate changes

  // --- Render Logic ---
  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (initializationError) {
      return <div>Error: {initializationError} Please try refreshing.</div>;
  }

  // If we are still loading or haven't determined project ID yet, show loading or nothing
  // This prevents rendering the Routes until projectId is ready for navigation effect
  if (!projectId) {
      console.log("Render: Waiting for projectId to be set..."); // Add log
      return <LoadingSpinner />; // Or null, or a minimal loading indicator
  }

  // Render Routes only when projectId is set and loading is complete
  console.log(`Render: ProjectId is ${projectId}, rendering Routes.`); // Add log
  return (
      <Routes>
        {/* Base path redirect is handled by the navigation effect now */}
        {/* <Route path="/" element={<Navigate to={`/${projectId}`} replace />} /> */}

        {/* Layout route needs userStatus */}
        <Route path="/" element={<Layout userStatus={userStatus} />}>
          {/* Define routes relative to the layout */}
          <Route path=":projectId" element={<ProjectHomePage />} />
          <Route path=":projectId/caller" element={<CallerPage />} />
          <Route path=":projectId/json-schema" element={<JsonSchemaPage />} />
          <Route path=":projectId/generate-dataset" element={<GenerateDatasetPage />} />
          <Route path=":projectId/requests/:requestId" element={<RequestDetailsPage />} />
          {/* Optional: Add a catch-all or index route within the project context if needed */}
           <Route index element={<Navigate to={`/${projectId}`} replace />} /> {/* Redirect index within layout */}
        </Route>
         {/* Optional: Add a top-level catch-all for invalid paths */}
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