import { DownloadDatasetComponent } from "@/components/download-dataset-component"

export default function GenerateDatasetPage() {
  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Generate Dataset</h1>
      <div className="max-w-2xl">
        <DownloadDatasetComponent sftAnnotatedResponses={5} dpoAnnotatedResponses={3} requiredResponses={20} />
      </div>
    </div>
  )
}
