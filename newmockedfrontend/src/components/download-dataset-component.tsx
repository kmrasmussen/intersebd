"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, ChevronUp, ChevronDown, AlertTriangle, RefreshCw } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AnnotationProgressBar } from "@/components/annotation-progress-bar"

interface DownloadDatasetComponentProps {
  className?: string
  title?: string
  description?: string
  requiredResponses?: number
  projectId: string
}

export function DownloadDatasetComponent({
  className = "",
  title = "Download Datasets",
  description = "Once you have annotated responses with rewards, you can download JSONL files for fine-tuning.",
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

  // DPO State
  const [dpoReadyCount, setDpoReadyCount] = useState(0)
  const [isRefreshingDpo, setIsRefreshingDpo] = useState(false)
  const [dpoError, setDpoError] = useState<string | null>(null)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
  const GUEST_USER_ID_HEADER = "X-Guest-User-Id"

  // Function to fetch SFT count
  const fetchSftCount = useCallback(async () => {
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

  // Function to fetch DPO ready count
  const fetchDpoReadyCount = useCallback(async () => {
    console.log(`DownloadDatasetComponent: fetchDpoReadyCount called. projectId: ${projectId}`);

    if (!projectId) {
      console.log("DownloadDatasetComponent: fetchDpoReadyCount aborted - no projectId.");
      return;
    }

    setIsRefreshingDpo(true);
    setDpoError(null);
    console.log(`DownloadDatasetComponent: Fetching DPO ready count for project ${projectId}`);

    const guestUserId = localStorage.getItem('guestUserId');
    const headers: HeadersInit = {};
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId;
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/dpo-ready-count?sft_threshold=0.75&dpo_negative_threshold=0.25`;

    try {
      const response = await fetch(url, { headers });
      if (!response.ok) {
        let errorDetail = `Failed to fetch DPO ready count: ${response.status}`;
        try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
        throw new Error(errorDetail);
      }
      const data = await response.json();
      setDpoReadyCount(data.dpo_ready_count);
      console.log(`DownloadDatasetComponent: DPO ready count fetched: ${data.dpo_ready_count}`);
    } catch (err: any) {
      console.error("DownloadDatasetComponent: Error fetching DPO ready count:", err);
      setDpoError(err.message || "Failed to load DPO ready count.");
      setDpoReadyCount(0); // Reset count on error
    } finally {
      setIsRefreshingDpo(false);
    }
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER]);

  // Fetch counts on initial load and when projectId changes
  useEffect(() => {
    console.log(`DownloadDatasetComponent: useEffect triggered. projectId: ${projectId}`);
    if (projectId) {
        fetchSftCount();
        fetchDpoReadyCount();
    } else {
        console.log("DownloadDatasetComponent: useEffect skipped fetches - no projectId yet.");
    }
  }, [projectId, fetchSftCount, fetchDpoReadyCount]);

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const handleDownloadSft = async () => {
    if (!projectId) {
      console.error("DownloadDatasetComponent: Cannot download SFT - projectId is missing.");
      setSftError("Project ID is missing.");
      return;
    }

    setIsDownloadingSft(true);
    setSftError(null);
    console.log(`DownloadDatasetComponent: Starting SFT dataset download for project ${projectId}`);

    const guestUserId = localStorage.getItem('guestUserId');
    const headers: HeadersInit = {};
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId;
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/sft-dataset.jsonl?sft_threshold=0.75`;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: headers,
      });

      if (!response.ok) {
        let errorDetail = `Failed to download SFT dataset: ${response.status}`;
        try { const errorData = await response.json(); errorDetail += ` - ${errorData.detail || 'Unknown error'}`; } catch { }
        throw new Error(errorDetail);
      }

      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `sft_dataset_${projectId}.jsonl`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }

      const blob = await response.blob();

      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();

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
    setDpoError(null)
    console.log("DPO Dataset download initiated (placeholder)");
    setTimeout(() => {
      setIsDownloadingDpo(false)
      console.log("DPO Dataset download finished (placeholder)")
    }, 1500)
  }

  const handleRefreshSft = () => {
    fetchSftCount();
  }

  const handleRefreshDpo = () => {
    fetchDpoReadyCount();
  }

  const isSftReady = sftRequestCount >= requiredResponses
  const isDpoReady = dpoReadyCount >= requiredResponses

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
                annotatedResponses={sftRequestCount}
                requiredResponses={requiredResponses}
                onRefresh={handleRefreshSft}
                isRefreshing={isRefreshingSft}
              />

              {dpoError && (
                 <Alert variant="destructive">
                   <AlertTriangle className="h-4 w-4" />
                   <AlertTitle>Error Loading DPO Count</AlertTitle>
                   <AlertDescription>{dpoError}</AlertDescription>
                 </Alert>
              )}
              <AnnotationProgressBar
                title="DPO Annotation Progress"
                annotatedResponses={dpoReadyCount}
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
            <Button className="gap-2 flex-1" onClick={handleDownloadDpo} disabled={isDownloadingDpo || !isDpoReady || isRefreshingDpo}>
              {isRefreshingDpo ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {isDownloadingDpo ? "Downloading..." : isRefreshingDpo ? "Refreshing..." : "Download DPO JSONL Dataset"}
            </Button>
          </CardFooter>
        </>
      )}
    </Card>
  )
}
