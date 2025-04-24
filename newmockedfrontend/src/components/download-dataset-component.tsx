"use client"

import { useState, useEffect, useCallback } from "react" // Added useCallback
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, ChevronUp, ChevronDown, AlertTriangle, RefreshCw } from "lucide-react" // Added RefreshCw
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AnnotationProgressBar } from "@/components/annotation-progress-bar"

interface DownloadDatasetComponentProps {
  className?: string
  title?: string
  description?: string
  dpoAnnotatedResponses?: number // Keep DPO mocked for now
  requiredResponses?: number
  projectId: string
}

export function DownloadDatasetComponent({
  className = "",
  title = "Download Datasets",
  description = "Once you have annotated responses with rewards, you can download JSONL files for fine-tuning.",
  dpoAnnotatedResponses: initialDpoAnnotatedResponses = 3, // Keep DPO mocked
  requiredResponses = 2,
  projectId
}: DownloadDatasetComponentProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [isDownloadingSft, setIsDownloadingSft] = useState(false)
  const [isDownloadingDpo, setIsDownloadingDpo] = useState(false)

  // SFT State
  const [sftRequestCount, setSftRequestCount] = useState(0)
  const [isRefreshingSft, setIsRefreshingSft] = useState(false)
  const [sftError, setSftError] = useState<string | null>(null)

  // DPO State (still mocked)
  const [isRefreshingDpo, setIsRefreshingDpo] = useState(false)
  const [dpoAnnotatedResponses, setDpoAnnotatedResponses] = useState(initialDpoAnnotatedResponses)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
  const GUEST_USER_ID_HEADER = "X-Guest-User-Id"

  // Function to fetch SFT count - Keep useCallback
  const fetchSftCount = useCallback(async () => {
    // Log inside useCallback to see if it's being created/called
    console.log(`DownloadDatasetComponent: fetchSftCount called. projectId: ${projectId}`);

    if (!projectId) {
      console.log("DownloadDatasetComponent: fetchSftCount aborted - no projectId.");
      return;
    }

    setIsRefreshingSft(true);
    setSftError(null);
    console.log(`DownloadDatasetComponent: Fetching SFT count for project ${projectId}`);

    const guestUserId = localStorage.getItem('guestUserId');
    const headers: HeadersInit = {};
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId;
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/sft-request-count`;

    try {
      const response = await fetch(url, { headers });
      if (!response.ok) {
        let errorDetail = `Failed to fetch SFT count: ${response.status}`;
        try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
        throw new Error(errorDetail);
      }
      const data = await response.json();
      setSftRequestCount(data.sft_request_count);
      console.log(`DownloadDatasetComponent: SFT count fetched: ${data.sft_request_count}`);
    } catch (err: any) {
      console.error("DownloadDatasetComponent: Error fetching SFT count:", err);
      setSftError(err.message || "Failed to load SFT count.");
      setSftRequestCount(0); // Reset count on error
    } finally {
      setIsRefreshingSft(false);
    }
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER]);

  // Fetch count on initial load and when projectId changes
  useEffect(() => {
    // Log inside useEffect to see if it runs and the projectId value at that time
    console.log(`DownloadDatasetComponent: useEffect triggered. projectId: ${projectId}`);
    // Only call fetch if projectId is truthy
    if (projectId) {
        fetchSftCount();
    } else {
        console.log("DownloadDatasetComponent: useEffect skipped fetch - no projectId yet.");
    }
  // *** Simplify dependency array to ONLY projectId ***
  }, [projectId]); // <--- CHANGE HERE

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const handleDownloadSft = async () => { // Make the function async
    if (!projectId) {
      console.error("DownloadDatasetComponent: Cannot download SFT - projectId is missing.");
      setSftError("Project ID is missing."); // Show error to user
      return;
    }

    setIsDownloadingSft(true);
    setSftError(null); // Clear previous errors
    console.log(`DownloadDatasetComponent: Starting SFT dataset download for project ${projectId}`);

    const guestUserId = localStorage.getItem('guestUserId');
    const headers: HeadersInit = {};
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId;
    }
    // Adjust threshold if needed, or remove if default 0.75 is always okay
    const url = `${API_BASE_URL}/mock-next/${projectId}/sft-dataset.jsonl?sft_threshold=0.75`;

    try {
      const response = await fetch(url, {
        method: 'GET', // Use GET for downloading
        headers: headers,
      });

      if (!response.ok) {
        let errorDetail = `Failed to download SFT dataset: ${response.status}`;
        try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
        throw new Error(errorDetail);
      }

      // Get filename from Content-Disposition header if available, otherwise use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `sft_dataset_${projectId}.jsonl`; // Default filename
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }

      // Get the response body as text (JSONL)
      const blob = await response.blob(); // Get as blob to handle file download

      // Create a temporary link to trigger the download
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename); // Use the determined filename
      document.body.appendChild(link);
      link.click();

      // Clean up the temporary link and URL object
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      console.log("DownloadDatasetComponent: SFT Dataset download initiated.");

    } catch (err: any) {
      console.error("DownloadDatasetComponent: Error downloading SFT dataset:", err);
      setSftError(err.message || "Failed to download SFT dataset.");
    } finally {
      setIsDownloadingSft(false);
    }
  };

  const handleDownloadDpo = () => {
    setIsDownloadingDpo(true)
    // Simulate download
    setTimeout(() => {
      setIsDownloadingDpo(false)
      console.log("DPO Dataset downloaded")
    }, 1500)
  }

  // Refresh SFT calls the fetch function
  const handleRefreshSft = () => {
    fetchSftCount();
  }

  // Keep DPO refresh mocked for now
  const handleRefreshDpo = () => {
    setIsRefreshingDpo(true)
    setTimeout(() => {
      const increase = Math.floor(Math.random() * 4)
      setDpoAnnotatedResponses((prev) => Math.min(requiredResponses, prev + increase))
      setIsRefreshingDpo(false)
    }, 1000)
  }

  const isSftReady = sftRequestCount >= requiredResponses
  const isDpoReady = dpoAnnotatedResponses >= requiredResponses // DPO still uses mocked value

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
              {sftError && (
                 <Alert variant="destructive">
                   <AlertTriangle className="h-4 w-4" />
                   <AlertTitle>Error Loading SFT Count</AlertTitle>
                   <AlertDescription>{sftError}</AlertDescription>
                 </Alert>
              )}
              <AnnotationProgressBar
                title="SFT Annotation Progress"
                annotatedResponses={sftRequestCount} // Use fetched count
                requiredResponses={requiredResponses}
                onRefresh={handleRefreshSft} // Use updated handler
                isRefreshing={isRefreshingSft} // Use SFT specific loading state
              />

              <AnnotationProgressBar
                title="DPO Annotation Progress"
                annotatedResponses={dpoAnnotatedResponses} // Keep mocked DPO
                requiredResponses={requiredResponses}
                onRefresh={handleRefreshDpo}
                isRefreshing={isRefreshingDpo}
              />

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
            <Button className="gap-2 flex-1" onClick={handleDownloadSft} disabled={isDownloadingSft || !isSftReady || isRefreshingSft}>
              {isRefreshingSft ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {isDownloadingSft ? "Downloading..." : isRefreshingSft ? "Refreshing..." : "Download SFT JSONL Dataset"}
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
