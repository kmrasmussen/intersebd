"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, ChevronUp, ChevronDown, AlertCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AnnotationProgressBar } from "@/components/annotation-progress-bar"

interface DownloadDatasetComponentProps {
  className?: string
  title?: string
  description?: string
  sftAnnotatedResponses?: number
  dpoAnnotatedResponses?: number
  requiredResponses?: number
}

export function DownloadDatasetComponent({
  className = "",
  title = "Download Datasets",
  description = "Once you have annotated responses with rewards, you can download JSONL files for fine-tuning.",
  sftAnnotatedResponses: initialSftAnnotatedResponses = 5,
  dpoAnnotatedResponses: initialDpoAnnotatedResponses = 3,
  requiredResponses = 20,
}: DownloadDatasetComponentProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [isDownloadingSft, setIsDownloadingSft] = useState(false)
  const [isDownloadingDpo, setIsDownloadingDpo] = useState(false)
  const [isRefreshingSft, setIsRefreshingSft] = useState(false)
  const [isRefreshingDpo, setIsRefreshingDpo] = useState(false)
  const [sftAnnotatedResponses, setSftAnnotatedResponses] = useState(initialSftAnnotatedResponses)
  const [dpoAnnotatedResponses, setDpoAnnotatedResponses] = useState(initialDpoAnnotatedResponses)

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const handleDownloadSft = () => {
    setIsDownloadingSft(true)
    // Simulate download
    setTimeout(() => {
      setIsDownloadingSft(false)
      console.log("SFT Dataset downloaded")
    }, 1500)
  }

  const handleDownloadDpo = () => {
    setIsDownloadingDpo(true)
    // Simulate download
    setTimeout(() => {
      setIsDownloadingDpo(false)
      console.log("DPO Dataset downloaded")
    }, 1500)
  }

  const handleRefreshSft = () => {
    setIsRefreshingSft(true)
    // Simulate fetching updated annotation count
    setTimeout(() => {
      // Simulate getting new data - in a real app this would be an API call
      const increase = Math.floor(Math.random() * 4)
      setSftAnnotatedResponses((prev) => Math.min(requiredResponses, prev + increase))
      setIsRefreshingSft(false)
    }, 1000)
  }

  const handleRefreshDpo = () => {
    setIsRefreshingDpo(true)
    // Simulate fetching updated annotation count
    setTimeout(() => {
      // Simulate getting new data - in a real app this would be an API call
      const increase = Math.floor(Math.random() * 4)
      setDpoAnnotatedResponses((prev) => Math.min(requiredResponses, prev + increase))
      setIsRefreshingDpo(false)
    }, 1000)
  }

  const isSftReady = sftAnnotatedResponses >= requiredResponses
  const isDpoReady = dpoAnnotatedResponses >= requiredResponses
  const isAnyDatasetNotReady = !isSftReady || !isDpoReady

  return (
    <Card className={`mb-6 ${className}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-md font-medium">{title}</CardTitle>
          {!collapsed && <CardDescription>{description}</CardDescription>}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={toggleCollapse}
          aria-label={collapsed ? "Expand dataset options" : "Collapse dataset options"}
        >
          {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </Button>
      </CardHeader>

      {!collapsed && (
        <>
          <CardContent>
            <div className="space-y-4">
              <AnnotationProgressBar
                title="SFT Annotation Progress"
                annotatedResponses={sftAnnotatedResponses}
                requiredResponses={requiredResponses}
                onRefresh={handleRefreshSft}
                isRefreshing={isRefreshingSft}
              />

              <AnnotationProgressBar
                title="DPO Annotation Progress"
                annotatedResponses={dpoAnnotatedResponses}
                requiredResponses={requiredResponses}
                onRefresh={handleRefreshDpo}
                isRefreshing={isRefreshingDpo}
              />

              {isAnyDatasetNotReady && (
                <Alert variant="warning" className="bg-amber-50 text-amber-800 border-amber-200">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please annotate more responses to reach the minimum requirement of {requiredResponses} annotated
                    responses for each dataset type.
                  </AlertDescription>
                </Alert>
              )}

              <div className="p-3 bg-gray-50 rounded-md">
                <p className="font-medium">Dataset Format</p>
                <p className="text-sm text-gray-500 mt-1">
                  The datasets will be exported as JSONL files with each line containing a complete conversation
                  including the request, response, and annotation metadata.
                </p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
            <Button className="gap-2 flex-1" onClick={handleDownloadSft} disabled={isDownloadingSft || !isSftReady}>
              <Download className="h-4 w-4" />
              {isDownloadingSft ? "Downloading..." : "Download SFT JSONL Dataset"}
            </Button>
            <Button className="gap-2 flex-1" onClick={handleDownloadDpo} disabled={isDownloadingDpo || !isDpoReady}>
              <Download className="h-4 w-4" />
              {isDownloadingDpo ? "Downloading..." : "Download DPO JSONL Dataset"}
            </Button>
          </CardFooter>
        </>
      )}
    </Card>
  )
}
