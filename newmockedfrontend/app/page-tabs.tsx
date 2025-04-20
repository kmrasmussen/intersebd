"use client"

import { useState } from "react"
import { CodeExample } from "@/components/code-example"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DownloadDatasetComponent } from "@/components/download-dataset-component"
import { SchemaEditorComponent } from "@/components/schema-editor-component"

export function PageTabs() {
  const [activeTab, setActiveTab] = useState<"api-call" | "schema-editor" | "finetune">("api-call")

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

      {activeTab === "api-call" ? (
        <CodeExample defaultPrompt="What is the capital of France?" title="Quick API Call" />
      ) : activeTab === "schema-editor" ? (
        <SchemaEditorComponent title="Quick Schema Edit" />
      ) : (
        <DownloadDatasetComponent
          title="Quick Dataset Download"
          description="Download JSONL datasets for fine-tuning based on your annotated responses."
          sftAnnotatedResponses={5}
          dpoAnnotatedResponses={3}
          requiredResponses={20}
        />
      )}
    </>
  )
}
