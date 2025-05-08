"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Download, ChevronUp, ChevronDown, AlertTriangle, RefreshCw, UploadCloud, CheckCircle, ExternalLink } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AnnotationProgressBar } from "@/components/annotation-progress-bar"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

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
  description = "Once you have annotated responses with rewards, you can download JSONL files or push directly to Hugging Face Hub.",
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
  const [isPushingSft, setIsPushingSft] = useState(false)
  const [sftPushError, setSftPushError] = useState<string | null>(null)
  const [showSftPushSuccessDialog, setShowSftPushSuccessDialog] = useState(false)
  const [sftPushResult, setSftPushResult] = useState<{ message: string; datasetPath: string | null } | null>(null)

  // DPO State
  const [dpoReadyCount, setDpoReadyCount] = useState(0)
  const [isRefreshingDpo, setIsRefreshingDpo] = useState(false)
  const [dpoError, setDpoError] = useState<string | null>(null)
  const [isPushingDpo, setIsPushingDpo] = useState(false)
  const [dpoPushError, setDpoPushError] = useState<string | null>(null)
  const [showDpoPushSuccessDialog, setShowDpoPushSuccessDialog] = useState(false)
  const [dpoPushResult, setDpoPushResult] = useState<{ message: string; datasetPath: string | null } | null>(null)

  // Hugging Face Credentials Dialog State
  const [showHfCredentialsDialog, setShowHfCredentialsDialog] = useState(false)
  const [hfDialogContext, setHfDialogContext] = useState<"sft" | "dpo" | null>(null) // New state for dialog context
  const [hfUsername, setHfUsername] = useState("")
  const [hfToken, setHfToken] = useState("")
  const [credentialDialogError, setCredentialDialogError] = useState<string | null>(null)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
  const GUEST_USER_ID_HEADER = "X-Guest-User-Id"

  const fetchSftCount = useCallback(async () => {
    if (!projectId) return

    setIsRefreshingSft(true)
    setSftError(null)
    setSftPushError(null)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/sft-request-count`

    try {
      const response = await fetch(url, { headers, credentials: "include" })
      if (!response.ok) {
        let errorDetail = `Failed to fetch SFT count: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch {}
        throw new Error(errorDetail)
      }
      const data = await response.json()
      setSftRequestCount(data.sft_request_count)
    } catch (err: any) {
      setSftError(err.message || "Failed to load SFT count.")
      setSftRequestCount(0)
    } finally {
      setIsRefreshingSft(false)
    }
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER])

  const fetchDpoReadyCount = useCallback(async () => {
    if (!projectId) return

    setIsRefreshingDpo(true)
    setDpoError(null)
    setDpoPushError(null)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/dpo-ready-count`

    try {
      const response = await fetch(url, { headers, credentials: "include" })
      if (!response.ok) {
        let errorDetail = `Failed to fetch DPO ready count: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch {}
        throw new Error(errorDetail)
      }
      const data = await response.json()
      setDpoReadyCount(data.dpo_ready_count)
    } catch (err: any) {
      setDpoError(err.message || "Failed to load DPO ready count.")
      setDpoReadyCount(0)
    } finally {
      setIsRefreshingDpo(false)
    }
  }, [projectId, API_BASE_URL, GUEST_USER_ID_HEADER])

  useEffect(() => {
    if (projectId) {
      fetchSftCount()
      fetchDpoReadyCount()
    }
  }, [projectId, fetchSftCount, fetchDpoReadyCount])

  const toggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const handleDownloadSft = async () => {
    if (!projectId) {
      setSftError("Project ID is missing.")
      return
    }

    setIsDownloadingSft(true)
    setSftError(null)
    setSftPushError(null)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/sft-dataset.jsonl`

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: headers,
        credentials: "include"
      })

      if (!response.ok) {
        let errorDetail = `Failed to download SFT dataset: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch {}
        throw new Error(errorDetail)
      }

      const contentDisposition = response.headers.get("Content-Disposition")
      let filename = `sft_dataset_${projectId}.jsonl`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1]
        }
      }

      const blob = await response.blob()

      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = downloadUrl
      link.setAttribute("download", filename)
      document.body.appendChild(link)
      link.click()

      link.parentNode?.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err: any) {
      setSftError(err.message || "Failed to download SFT dataset.")
    } finally {
      setIsDownloadingSft(false)
    }
  }

  const handleDownloadDpo = async () => {
    if (!projectId) {
      setDpoError("Project ID is missing.")
      return
    }

    setIsDownloadingDpo(true)
    setDpoError(null)
    setDpoPushError(null)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/dpo-dataset.jsonl`

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: headers,
        credentials: "include"
      })

      if (!response.ok) {
        let errorDetail = `Failed to download DPO dataset: ${response.status}`
        try {
          const errorData = await response.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch {}
        throw new Error(errorDetail)
      }

      const contentDisposition = response.headers.get("Content-Disposition")
      let filename = `dpo_dataset_${projectId}.jsonl`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1]
        }
      }

      const blob = await response.blob()

      if (blob.size === 0) {
        setDpoError("No DPO data available to download for the current criteria.")
        setIsDownloadingDpo(false)
        return
      }

      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = downloadUrl
      link.setAttribute("download", filename)
      document.body.appendChild(link)
      link.click()

      link.parentNode?.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err: any) {
      setDpoError(err.message || "Failed to download DPO dataset.")
    } finally {
      setIsDownloadingDpo(false)
    }
  }

  const handlePushSftToHub = async (username: string, token: string) => {
    if (!projectId) {
      console.error("DownloadDatasetComponent: Cannot push SFT to Hub - projectId is missing.")
      setSftPushError("Project ID is missing.")
      return
    }

    setIsPushingSft(true)
    setSftError(null)
    setSftPushError(null)
    console.log(`DownloadDatasetComponent: Starting SFT dataset push to Hub for project ${projectId}`)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = { "Content-Type": "application/json" }
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/push-sft-dataset-to-hub`

    const body = JSON.stringify({
      hf_username: username,
      hf_write_access_token: token,
      do_push: true
    })

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: headers,
        body: body,
        credentials: "include"
      })

      const responseData = await response.json()

      if (!response.ok) {
        let errorDetail = `Failed to push SFT dataset to Hub: ${response.status}`
        errorDetail += ` - ${responseData.detail || "Unknown server error"}`
        throw new Error(errorDetail)
      }

      console.log("DownloadDatasetComponent: SFT Dataset push successful:", responseData)
      setSftPushResult({
        message: responseData.message || "Operation successful.",
        datasetPath: responseData.dataset_path || null
      })
      setShowSftPushSuccessDialog(true)
      setShowHfCredentialsDialog(false)
    } catch (err: any) {
      console.error("DownloadDatasetComponent: Error pushing SFT dataset to Hub:", err)
      setSftPushError(err.message || "Failed to push SFT dataset to Hub.")
    } finally {
      setIsPushingSft(false)
    }
  }

  const handlePushDpoToHub = async (username: string, token: string) => {
    if (!projectId) {
      console.error("DownloadDatasetComponent: Cannot push DPO to Hub - projectId is missing.")
      setDpoPushError("Project ID is missing.")
      return
    }

    setIsPushingDpo(true)
    setDpoError(null)
    setDpoPushError(null)
    console.log(`DownloadDatasetComponent: Starting DPO dataset push to Hub for project ${projectId}`)

    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = { "Content-Type": "application/json" }
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }
    const url = `${API_BASE_URL}/mock-next/${projectId}/push-dpo-dataset-to-hub`

    const body = JSON.stringify({
      hf_username: username,
      hf_write_access_token: token,
      do_push: true
    })

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: headers,
        body: body,
        credentials: "include"
      })

      const responseData = await response.json()

      if (!response.ok) {
        let errorDetail = `Failed to push DPO dataset to Hub: ${response.status}`
        errorDetail += ` - ${responseData.detail || "Unknown server error"}`
        throw new Error(errorDetail)
      }

      console.log("DownloadDatasetComponent: DPO Dataset push successful:", responseData)
      setDpoPushResult({
        message: responseData.message || "Operation successful.",
        datasetPath: responseData.dataset_path || null
      })
      setShowDpoPushSuccessDialog(true)
      setShowHfCredentialsDialog(false)
    } catch (err: any) {
      console.error("DownloadDatasetComponent: Error pushing DPO dataset to Hub:", err)
      setDpoPushError(err.message || "Failed to push DPO dataset to Hub.")
    } finally {
      setIsPushingDpo(false)
    }
  }

  const submitHfCredentials = () => {
    setCredentialDialogError(null)
    if (!hfUsername.trim()) {
      setCredentialDialogError("Hugging Face username is required.")
      return
    }
    if (!hfToken.trim()) {
      setCredentialDialogError("Hugging Face write token is required.")
      return
    }

    if (hfDialogContext === "sft") {
      handlePushSftToHub(hfUsername, hfToken)
    } else if (hfDialogContext === "dpo") {
      handlePushDpoToHub(hfUsername, hfToken)
    } else {
      setCredentialDialogError("Invalid operation context.")
      console.error("submitHfCredentials called with invalid hfDialogContext:", hfDialogContext)
    }
  }

  const handleRefreshSft = () => {
    fetchSftCount()
  }

  const handleRefreshDpo = () => {
    fetchDpoReadyCount()
  }

  const isSftReady = sftRequestCount >= requiredResponses
  const isDpoReady = dpoReadyCount >= requiredResponses

  const isSftBusy = isRefreshingSft || isDownloadingSft || isPushingSft
  const isDpoBusy = isRefreshingDpo || isDownloadingDpo || isPushingDpo
  const isDialogBusy = (hfDialogContext === "sft" && isPushingSft) || (hfDialogContext === "dpo" && isPushingDpo)

  return (
    <>
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
                    <AlertTitle>Error Loading SFT Data</AlertTitle>
                    <AlertDescription>{sftError}</AlertDescription>
                  </Alert>
                )}
                {sftPushError && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error Pushing SFT Dataset</AlertTitle>
                    <AlertDescription>{sftPushError}</AlertDescription>
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
                    <AlertTitle>Error Loading DPO Data</AlertTitle>
                    <AlertDescription>{dpoError}</AlertDescription>
                  </Alert>
                )}
                {dpoPushError && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error Pushing DPO Dataset</AlertTitle>
                    <AlertDescription>{dpoPushError}</AlertDescription>
                  </Alert>
                )}
                <AnnotationProgressBar
                  title="DPO Annotation Progress"
                  annotatedResponses={dpoReadyCount}
                  requiredResponses={requiredResponses}
                  onRefresh={handleRefreshDpo}
                  isRefreshing={isRefreshingDpo}
                />
              </div>
            </CardContent>
            <CardFooter className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Button className="gap-2" onClick={handleDownloadSft} disabled={!isSftReady || isSftBusy}>
                {isDownloadingSft ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                {isDownloadingSft ? "Downloading..." : "Download SFT JSONL"}
              </Button>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => {
                  setHfDialogContext("sft")
                  setHfUsername("")
                  setHfToken("")
                  setCredentialDialogError(null)
                  setShowHfCredentialsDialog(true)
                }}
                disabled={!isSftReady || isSftBusy}
              >
                {isPushingSft && hfDialogContext === "sft" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                Push SFT to Hub
              </Button>

              <Button className="gap-2" onClick={handleDownloadDpo} disabled={!isDpoReady || isDpoBusy}>
                {isDownloadingDpo ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                {isDownloadingDpo ? "Downloading..." : "Download DPO JSONL"}
              </Button>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => {
                  setHfDialogContext("dpo")
                  setHfUsername("")
                  setHfToken("")
                  setCredentialDialogError(null)
                  setShowHfCredentialsDialog(true)
                }}
                disabled={!isDpoReady || isDpoBusy}
              >
                {isPushingDpo && hfDialogContext === "dpo" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                Push DPO to Hub
              </Button>
            </CardFooter>
          </>
        )}
      </Card>

      <Dialog open={showHfCredentialsDialog} onOpenChange={(isOpen) => {
        if (isDialogBusy) return
        setShowHfCredentialsDialog(isOpen)
        if (!isOpen) setHfDialogContext(null)
      }}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>
              Push {hfDialogContext?.toUpperCase()} Dataset to Hugging Face Hub
            </DialogTitle>
            <DialogDescription>
              Enter your Hugging Face username and a write access token to push the dataset. The token will only be used for this request.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="hf-username" className="text-right">
                Username
              </Label>
              <Input
                id="hf-username"
                value={hfUsername}
                onChange={(e) => setHfUsername(e.target.value)}
                className="col-span-3"
                placeholder="Your HF Username"
                disabled={isDialogBusy}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="hf-token" className="text-right">
                Token
              </Label>
              <Input
                id="hf-token"
                type="password"
                value={hfToken}
                onChange={(e) => setHfToken(e.target.value)}
                className="col-span-3"
                placeholder="hf_YourWriteAccessToken"
                disabled={isDialogBusy}
              />
            </div>
            {credentialDialogError && (
              <Alert variant="destructive" className="col-span-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{credentialDialogError}</AlertDescription>
              </Alert>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
                setShowHfCredentialsDialog(false)
                setHfDialogContext(null)
            }} disabled={isDialogBusy}>
              Cancel
            </Button>
            <Button onClick={submitHfCredentials} disabled={isDialogBusy}>
              {isDialogBusy ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : null}
              {isDialogBusy ? `Pushing ${hfDialogContext?.toUpperCase()}...` : `Push ${hfDialogContext?.toUpperCase()} to Hub`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showSftPushSuccessDialog} onOpenChange={setShowSftPushSuccessDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" /> SFT Push Successful
            </DialogTitle>
            <DialogDescription>{sftPushResult?.message || "The SFT dataset operation completed successfully."}</DialogDescription>
          </DialogHeader>
          {sftPushResult?.datasetPath && (
            <div className="mt-4 text-sm">
              Dataset Path:
              <a
                href={`https://huggingface.co/datasets/${sftPushResult.datasetPath}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                {sftPushResult.datasetPath}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowSftPushSuccessDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showDpoPushSuccessDialog} onOpenChange={setShowDpoPushSuccessDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" /> DPO Push Successful
            </DialogTitle>
            <DialogDescription>{dpoPushResult?.message || "The DPO dataset operation completed successfully."}</DialogDescription>
          </DialogHeader>
          {dpoPushResult?.datasetPath && (
            <div className="mt-4 text-sm">
              Dataset Path:
              <a
                href={`https://huggingface.co/datasets/${dpoPushResult.datasetPath}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                {dpoPushResult.datasetPath}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowDpoPushSuccessDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
