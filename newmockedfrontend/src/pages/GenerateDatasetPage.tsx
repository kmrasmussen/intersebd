"use client";

import { useParams } from "react-router-dom";
import { DownloadDatasetComponent } from "@/components/download-dataset-component";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function GenerateDatasetPage() {
  const { projectId } = useParams<{ projectId: string }>();

  if (!projectId) {
    return (
      <div className="container mx-auto py-4">
        <h1 className="text-2xl font-bold mb-6">Generate Fine-tuning Datasets</h1>
        <div>Loading project details...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Generate Fine-tuning Datasets</h1>
      <Card>
        <CardHeader>
          <CardTitle>Download Options</CardTitle>
          <CardDescription>
            Generate and download JSONL datasets based on your annotations. Ensure you have enough annotated
            responses.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DownloadDatasetComponent
            sftAnnotatedResponses={5}
            dpoAnnotatedResponses={3}
            requiredResponses={20}
            projectId={projectId}
          />
        </CardContent>
      </Card>
    </div>
  );
}
