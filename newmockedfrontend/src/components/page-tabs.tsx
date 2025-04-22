"use client"

import { useState } from "react"
import { CodeExample } from "@/components/code-example"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DownloadDatasetComponent } from "@/components/download-dataset-component"
import { SchemaEditorComponent } from "@/components/schema-editor-component"

// Define props interface to accept projectId
interface PageTabsProps {
  projectId: string;
}

// Accept projectId as a prop
export function PageTabs({ projectId }: PageTabsProps) {
  const [activeTab, setActiveTab] = useState<"api-call" | "schema-editor" | "finetune">("api-call")

  // You can now use the projectId prop within this component if needed
  console.log("Project ID in PageTabs:", projectId);

  return (
    <>
      <div className="mb-4">
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as "api-call" | "schema-editor" | "finetune")}
        >
          <TabsList>
            <TabsTrigger value="api-call">API Call</TabsTrigger>
            <TabsTrigger value="schema-editor">Schema Editor</TabsTrigger>
            <TabsTrigger value="finetune">Finetune</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Pass projectId down to child components if they need it */}
      {activeTab === "api-call" ? (
        <CodeExample
          defaultPrompt="What is the capital of France?"
          title="Quick API Call"
          projectId={projectId}
        />
      ) : activeTab === "schema-editor" ? (
        <SchemaEditorComponent
          title="Quick Schema Edit"
          // projectId={projectId} // Pass if SchemaEditorComponent needs it
        />
      ) : (
        <DownloadDatasetComponent
          title="Quick Dataset Download"
          description="Download JSONL datasets for fine-tuning based on your annotated responses."
          sftAnnotatedResponses={5} // Example value
          dpoAnnotatedResponses={3} // Example value
          requiredResponses={20} // Example value
          // projectId={projectId} // Pass if DownloadDatasetComponent needs it
        />
      )}
    </>
  )
}
