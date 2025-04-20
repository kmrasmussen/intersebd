import { RequestsOverviewV2 } from "@/components/requests-overview-v2"
import { PageTabs } from "@/app/page-tabs"

export default function Home() {
  return (
    <div className="container mx-auto py-4">
      <h1 className="text-2xl font-bold mb-6">Requests Overview</h1>
      <PageTabs />
      <RequestsOverviewV2 />
    </div>
  )
}
