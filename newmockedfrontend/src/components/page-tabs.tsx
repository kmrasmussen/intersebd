"use client"

import { useState, useEffect } from "react"
import { CodeExample } from "@/components/code-example"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { DownloadDatasetComponent } from "@/components/download-dataset-component"
import { SchemaEditorComponent } from "@/components/schema-editor-component"
import { AlertCircle } from "lucide-react"

// Define props interface
interface PageTabsProps {
  projectId: string;
  onApiCallSuccess: () => void; // <-- Accept the callback prop
}

// Placeholder/Initial state for schema
const initialSchemaValue = "";

// Accept projectId and onApiCallSuccess as props
export function PageTabs({ projectId, onApiCallSuccess }: PageTabsProps) {
  const [activeTab, setActiveTab] = useState<"api-call" | "schema-editor" | "finetune">("api-call")

  const [currentSchema, setCurrentSchema] = useState(initialSchemaValue);
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [isSchemaEmptyState, setIsSchemaEmptyState] = useState(false);

  useEffect(() => {
    if (!projectId) return;

    const fetchCurrentSchemaForTabs = async () => {
      if (currentSchema !== initialSchemaValue && !schemaError && !isLoadingSchema) return;

      setIsLoadingSchema(true);
      setSchemaError(null);
      setIsSchemaEmptyState(false);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
      const GUEST_USER_ID_HEADER = "X-Guest-User-Id";
      const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/schemas/current`;
      const guestUserId = localStorage.getItem('guestUserId');
      const headers: HeadersInit = {};
      if (guestUserId) {
        headers[GUEST_USER_ID_HEADER] = guestUserId;
      }

      console.log(`PageTabs: Fetching current schema from ${apiUrl}`);

      try {
        const response = await fetch(apiUrl, { headers });
        if (!response.ok) {
          if (response.status === 404) {
            setSchemaError("No active schema found. Create one in the editor.");
            setCurrentSchema(initialSchemaValue);
            setIsSchemaEmptyState(true);
          } else {
            let errorDetail = `HTTP error! status: ${response.status}`;
            try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { /* Ignore */ }
            throw new Error(errorDetail);
          }
        } else {
          const schemaData = await response.json();
          setCurrentSchema(JSON.stringify(schemaData.schema_content, null, 2));
          setIsSchemaEmptyState(false);
        }
      } catch (error: any) {
        console.error("PageTabs: Failed to fetch current schema:", error);
        setSchemaError(error.message || "Failed to load schema");
        setCurrentSchema(initialSchemaValue);
        setIsSchemaEmptyState(true);
      } finally {
        setIsLoadingSchema(false);
      }
    };

    fetchCurrentSchemaForTabs();
  }, [projectId]);

  const handleSchemaSavedInTabs = (newSchemaData: any) => {
    try {
      setCurrentSchema(JSON.stringify(newSchemaData.schema_content, null, 2));
      setIsSchemaEmptyState(false);
      setSchemaError(null);
    } catch (error) {
      console.error("PageTabs: Error formatting saved schema:", error);
      setSchemaError("Error updating schema display after save.");
    }
  };

  return (
    <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "api-call" | "schema-editor" | "finetune")} className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-4">
        <TabsTrigger value="api-call">API Call</TabsTrigger>
        <TabsTrigger value="schema-editor">Schema Editor</TabsTrigger>
        <TabsTrigger value="finetune">Finetune</TabsTrigger>
      </TabsList>

      <TabsContent value="api-call">
        <CodeExample
          defaultPrompt="What is the capital of France?"
          title="Quick API Call"
          projectId={projectId}
          onCallSuccess={onApiCallSuccess} // <-- Pass the callback down
        />
      </TabsContent>

      <TabsContent value="schema-editor">
        {isLoadingSchema && <div>Loading schema...</div>}
        {schemaError && !isLoadingSchema && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{schemaError}</span>
          </div>
        )}
        {!isLoadingSchema && (
          <SchemaEditorComponent
            title="Project Schema"
            projectId={projectId}
            initialSchema={currentSchema}
            onSchemaSaved={handleSchemaSavedInTabs}
            isEmptyState={isSchemaEmptyState}
          />
        )}
      </TabsContent>

      <TabsContent value="finetune">
        <DownloadDatasetComponent
          title="Quick Dataset Download"
          description="Download JSONL datasets for fine-tuning based on your annotated responses."
          requiredResponses={10}
          projectId={projectId}
        />
      </TabsContent>
    </Tabs>
  );
}
