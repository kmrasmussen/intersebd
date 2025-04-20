import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function AboutPage() {
  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">About</h1>

      <div className="max-w-3xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Annotation Tool</CardTitle>
            <CardDescription>
              A tool for annotating AI responses and generating datasets for fine-tuning
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="font-medium text-lg">Overview</h3>
              <p className="text-gray-600 mt-1">
                This tool allows you to review AI-generated responses, annotate them with rewards, and generate datasets
                that can be used for fine-tuning language models.
              </p>
            </div>

            <div>
              <h3 className="font-medium text-lg">How to Use</h3>
              <ol className="list-decimal list-inside space-y-2 mt-1 text-gray-600">
                <li>Browse the requests in the Requests Overview page</li>
                <li>Click on a request to view its details and responses</li>
                <li>Annotate responses with rewards based on quality</li>
                <li>Generate and download datasets for fine-tuning</li>
              </ol>
            </div>

            <div>
              <h3 className="font-medium text-lg">Annotation Guidelines</h3>
              <p className="text-gray-600 mt-1">When annotating responses, consider the following criteria:</p>
              <ul className="list-disc list-inside space-y-1 mt-1 text-gray-600">
                <li>Accuracy: Does the response correctly answer the question?</li>
                <li>Clarity: Is the response clear and easy to understand?</li>
                <li>Completeness: Does the response fully address all aspects of the question?</li>
                <li>Helpfulness: Is the response helpful to the user?</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Version Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Version</div>
              <div>1.0.0</div>

              <div className="text-gray-500">Last Updated</div>
              <div>April 19, 2025</div>

              <div className="text-gray-500">Supported Models</div>
              <div>OpenAI GPT-4.1, GPT-4, GPT-3.5</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
