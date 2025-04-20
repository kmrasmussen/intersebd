import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout"; // We'll create/move this
import ProjectHomePage from "./pages/ProjectHomePage"; // We'll move this
import CallerPage from "./pages/CallerPage"; // We'll move/create this
import JsonSchemaPage from "./pages/JsonSchemaPage"; // We'll move/create this
import GenerateDatasetPage from "./pages/GenerateDatasetPage"; // We'll move/create this
import RequestDetailsPage from "./pages/RequestDetailsPage"; // Corrected import path

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Use Layout for routes that need the sidebar */}
        <Route path="/" element={<Layout />}>
          {/* Project specific routes */}
          <Route path=":projectId" element={<ProjectHomePage />} />
          <Route path=":projectId/caller" element={<CallerPage />} />
          <Route path=":projectId/json-schema" element={<JsonSchemaPage />} />
          <Route path=":projectId/generate-dataset" element={<GenerateDatasetPage />} />
          {/* Added route for request details */}
          <Route path=":projectId/requests/:requestId" element={<RequestDetailsPage />} />

          {/* Optional: Add an index route for the root if needed */}
          {/* <Route index element={<SomeRootPageComponent />} /> */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;