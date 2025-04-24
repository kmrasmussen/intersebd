"use client"

import { useState, useMemo, useEffect } from "react"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Check, RefreshCw, X, ThumbsUp, ThumbsDown, Trash2, Copy, CheckCircle2, XCircle, AlertCircle, FileJson, FileText } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"

import Form from '@rjsf/core';
import { RJSFSchema, RJSFValidationError, UiSchema, FieldTemplateProps, WidgetProps, BaseInputTemplateProps } from '@rjsf/utils';
import validator from '@rjsf/validator-ajv8';

type Annotation = {
  id: string
  reward: number
  by: string
  at: string
}

type ResponseMetadata = {
  completion_id?: string
  annotation_target_id?: string
  provider?: string
  model?: string
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  choice_finish_reason?: string
  choice_role?: string
  choice_content?: string
  [key: string]: any
}

type Response = {
  id: string
  annotation_target_id?: string | null
  content: string 
  model: string
  created: string
  annotations: Annotation[]
  metadata?: ResponseMetadata
  is_json: boolean
  obeys_schema: boolean | null
}

interface ResponseCardProps {
  response: Response
  isAlternative?: boolean
  projectId: string
  onAnnotationAdded?: (targetId: string, newAnnotationData: any) => void
  onResponseDeleted?: (targetId: string) => void
  onAnnotationDeleted?: (targetId: string, annotationId: string) => void
  activeSchema: RJSFSchema | null
}

function JsonFormatter({ jsonString }: { jsonString: string }) {
  const [copied, setCopied] = useState(false)

  const formattedJson = useMemo(() => {
    try {
      const parsed = JSON.parse(jsonString)
      return JSON.stringify(parsed, null, 2)
    } catch (e) {
      return jsonString
    }
  }, [jsonString])

  const highlightJson = (json: string) => {
    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        let cls = "text-purple-600"
        if (/^"/.test(match) && /:$/.test(match)) {
          cls = "text-red-600"
        } else if (/true|false/.test(match)) {
          cls = "text-blue-600"
        } else if (/null/.test(match)) {
          cls = "text-gray-600"
        } else if (/^-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?$/.test(match)) {
          cls = "text-green-600"
        }
        return `<span class="${cls}">${match}</span>`
      },
    )
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error("Failed to copy text: ", err)
    }
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-2 right-2 h-7 w-7 p-0 bg-gray-100 hover:bg-gray-200 rounded-md z-10"
        onClick={handleCopy}
        title="Copy JSON"
      >
        {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-gray-500" />}
        <span className="sr-only">Copy JSON</span>
      </Button>
      <pre className="bg-gray-50 p-3 rounded-md overflow-auto text-xs font-mono">
        <code dangerouslySetInnerHTML={{ __html: highlightJson(formattedJson) }} />
      </pre>
    </div>
  )
}

// --- START: Define Custom Shadcn Field Template ---
function ShadcnFieldTemplate(props: FieldTemplateProps) {
  const { id, classNames, style, label, help, required, description, errors, children, hidden, displayLabel } = props;

  // Don't render hidden fields
  if (hidden) {
    return <div style={{ display: 'none' }}>{children}</div>;
  }

  return (
    <div className={classNames + " mb-4"} style={style}> {/* Add margin bottom */}
      {/* Render label if displayLabel is true */}
      {displayLabel && label && (
        <Label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1"> {/* Basic label styling */}
          {label}
          {required ? <span className="text-destructive">*</span> : null}
        </Label>
      )}

      {/* Render the actual input widget */}
      {children}

      {/* Render description below the input */}
      {displayLabel && description ? description : null}

      {/* Render errors below the input/description */}
      {errors ? <div className="mt-1 text-sm text-destructive">{errors}</div> : null}

      {/* Render help text below errors */}
      {help ? <div className="mt-1 text-sm text-muted-foreground">{help}</div> : null}
    </div>
  );
}
// --- END: Define Custom Shadcn Field Template ---

// --- Custom Widgets ---

// Custom BaseInputTemplate to replace the default input rendering
function ShadcnBaseInputTemplate(props: BaseInputTemplateProps) {
  const {
    id,
    placeholder,
    required,
    readonly,
    disabled,
    type,
    value,
    onChange,
    onBlur,
    onFocus,
    autofocus,
    options,
    schema,
    rawErrors = [],
  } = props;

  // Don't attempt to render buttons
  if (type === 'button' || type === 'submit' || type === 'reset') {
    return null;
  }

  const inputProps = {
    id,
    placeholder,
    disabled: disabled || readonly,
    required,
    autoFocus: autofocus,
    value: value || '',
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value),
    onBlur: onBlur && ((event: React.FocusEvent<HTMLInputElement>) => onBlur(id, event.target.value)),
    onFocus: onFocus && ((event: React.FocusEvent<HTMLInputElement>) => onFocus(id, event.target.value)),
  };
  
  // For textarea inputs (explicitly set in schema or for strings with format="textarea")
  if (
    schema.type === "string" && 
    (schema.format === "textarea" || options.widget === "textarea")
  ) {
    return (
      <Textarea
        {...inputProps}
        className={`w-full ${rawErrors.length > 0 ? 'border-red-500' : ''}`}
        onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => onChange(event.target.value)}
      />
    );
  }
  
  // For all other inputs
  return (
    <Input
      type={type || "text"}
      {...inputProps}
      className={`w-full ${rawErrors.length > 0 ? 'border-red-500' : ''}`}
    />
  );
}

// Custom CheckboxWidget
function ShadcnCheckboxWidget(props: WidgetProps) {
  const { 
    id, 
    value, 
    disabled, 
    readonly, 
    onChange, 
    label, 
    schema, 
    required 
  } = props;
  
  return (
    <div className="flex items-center space-x-2">
      <Checkbox
        id={id}
        checked={typeof value === "undefined" ? false : value}
        disabled={disabled || readonly}
        onCheckedChange={(checked) => onChange(checked)}
      />
      <label htmlFor={id} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
        {label || schema.title}
        {required ? <span className="text-red-500">*</span> : null}
      </label>
    </div>
  );
}

export function ResponseCard({
  response,
  isAlternative = false,
  projectId,
  onAnnotationAdded,
  onResponseDeleted,
  onAnnotationDeleted,
  activeSchema,
}: ResponseCardProps) {
  const [viewMode, setViewMode] = useState<'default' | 'raw' | 'form'>('default')
  const [hideAnnotations, setHideAnnotations] = useState(false)
  const [isAnnotating, setIsAnnotating] = useState(false)
  const [annotationError, setAnnotationError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deletingAnnotationId, setDeletingAnnotationId] = useState<string | null>(null)
  const [annotationDeleteError, setAnnotationDeleteError] = useState<string | null>(null)
  const [isSftExample, setIsSftExample] = useState<boolean | null>(null)
  const [isSftLoading, setIsSftLoading] = useState(false)

  useEffect(() => {
    const checkSftStatus = async () => {
      if (!response.annotation_target_id) return;
      
      setIsSftLoading(true);
      
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
      const GUEST_USER_ID_HEADER = "X-Guest-User-Id";
      const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotation-targets/${response.annotation_target_id}/is-sft`;
      const guestUserId = localStorage.getItem("guestUserId");
      const headers: HeadersInit = {};
      
      if (guestUserId) {
        headers[GUEST_USER_ID_HEADER] = guestUserId;
      }

      try {
        const apiResponse = await fetch(apiUrl, {
          method: "GET",
          headers
        });

        if (!apiResponse.ok) {
          console.error(`Failed to check SFT status: ${apiResponse.status}`);
          setIsSftExample(null);
          return;
        }

        const isSft = await apiResponse.json();
        setIsSftExample(isSft);
      } catch (error) {
        console.error("Error checking SFT status:", error);
        setIsSftExample(null);
      } finally {
        setIsSftLoading(false);
      }
    };

    if (response.annotations.length > 0) {
      checkSftStatus();
    } else {
      setIsSftExample(false); // No annotations means not an SFT example
    }
  }, [response.annotation_target_id, response.annotations, projectId]);

  const formData = useMemo(() => {
    if (viewMode === 'form' && response.is_json && response.content) {
      try {
        return JSON.parse(response.content)
      } catch (e) {
        console.error("Error parsing JSON for form view:", e)
        return null
      }
    }
    return null
  }, [viewMode, response.is_json, response.content])

  const canShowFormView = response.is_json && response.obeys_schema === true && activeSchema !== null

  const toggleViewMode = (mode: 'default' | 'raw' | 'form') => {
    if (viewMode === 'form' && mode !== 'form') {
      setViewMode('default')
    } else if (viewMode === 'raw' && mode !== 'raw') {
      setViewMode('default')
    } else {
      setViewMode(mode)
    }
  }

  const handleDeleteResponse = async () => {
    const targetId = response.annotation_target_id
    if (!targetId) {
      console.error("Annotation target ID is missing for deletion:", response.id)
      setDeleteError("Cannot delete: Missing target ID.")
      return
    }

    setIsDeleting(true)
    setDeleteError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotation-targets/${targetId}`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "DELETE",
        headers: headers,
      })

      if (!apiResponse.ok && apiResponse.status !== 204) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {}
        throw new Error(errorDetail)
      }

      if (onResponseDeleted) {
        onResponseDeleted(targetId)
      }
    } catch (error: any) {
      setDeleteError(error.message || "Failed to delete target")
    } finally {
      setIsDeleting(false)
    }
  }

  const handleAnnotationSubmit = async (reward: number) => {
    const targetId = response.annotation_target_id
    if (!targetId) {
      setAnnotationError("Cannot annotate: Missing target ID.")
      return
    }

    setIsAnnotating(true)
    setAnnotationError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotation-targets/${targetId}/annotations`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    const body = JSON.stringify({
      reward: reward,
      annotation_metadata: { submittedFrom: "ResponseCard" },
    })

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "POST",
        headers: headers,
        body: body,
      })

      if (!apiResponse.ok) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {}
        throw new Error(errorDetail)
      }

      const newAnnotationData = await apiResponse.json()

      if (onAnnotationAdded) {
        onAnnotationAdded(targetId, newAnnotationData)
      }
    } catch (error: any) {
      setAnnotationError(error.message || "Failed to submit annotation")
    } finally {
      setIsAnnotating(false)
    }
  }

  const handleDeleteAnnotation = async (annotationId: string) => {
    const targetId = response.annotation_target_id
    if (!targetId) {
      setAnnotationDeleteError("Cannot delete annotation: Response target ID missing.")
      return
    }

    setDeletingAnnotationId(annotationId)
    setAnnotationDeleteError(null)

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
    const GUEST_USER_ID_HEADER = "X-Guest-User-Id"
    const apiUrl = `${API_BASE_URL}/mock-next/${projectId}/annotations/${annotationId}`
    const guestUserId = localStorage.getItem("guestUserId")
    const headers: HeadersInit = {}
    if (guestUserId) {
      headers[GUEST_USER_ID_HEADER] = guestUserId
    }

    try {
      const apiResponse = await fetch(apiUrl, {
        method: "DELETE",
        headers: headers,
      })

      if (!apiResponse.ok && apiResponse.status !== 204) {
        let errorDetail = `HTTP error! status: ${apiResponse.status}`
        try {
          const errorData = await apiResponse.json()
          errorDetail += ` - ${errorData.detail || "Unknown error"}`
        } catch (jsonError) {}
        throw new Error(errorDetail)
      }

      if (onAnnotationDeleted) {
        onAnnotationDeleted(targetId, annotationId)
      }
    } catch (error: any) {
      setAnnotationDeleteError(`Failed to delete annotation ${annotationId}: ${error.message || "Unknown error"}`)
    } finally {
      setDeletingAnnotationId(null)
    }
  }

  const uiSchema: UiSchema = useMemo(() => {
    return {
      "ui:classNames": "space-y-4",
      "ui:options": {
        className: "w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
      },
    };
  }, []);

  const templates = {
    FieldTemplate: ShadcnFieldTemplate,
    BaseInputTemplate: ShadcnBaseInputTemplate,
  };

  const widgets = {
    CheckboxWidget: ShadcnCheckboxWidget,
  };

  return (
    <Card className="border-gray-200">
      <CardHeader className="bg-gray-50 py-3 px-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant={isAlternative ? "secondary" : "default"}
              className={isAlternative ? "bg-gray-200 text-gray-800" : ""}
            >
              {isAlternative ? "Alternative" : "Response"}
            </Badge>
            <span className="text-sm text-gray-500">{new Date(response.created).toLocaleString()}</span>

            {isSftLoading ? (
              <Badge variant="outline" className="bg-gray-100 text-gray-600 flex items-center gap-1">
                <RefreshCw className="h-3 w-3 animate-spin" /> SFT...
              </Badge>
            ) : isSftExample === true ? (
              <Badge variant="outline" className="bg-green-50 text-green-600 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> SFT Example
              </Badge>
            ) : response.annotations.length > 0 ? (
              <Badge variant="outline" className="bg-amber-50 text-amber-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> Not SFT
              </Badge>
            ) : null}

            {!response.is_json && (
              <Badge variant="outline" className="bg-red-50 text-red-600 flex items-center gap-1">
                <XCircle className="h-3 w-3" /> Not JSON
              </Badge>
            )}
            {response.is_json && (
              <Badge variant="outline" className="bg-blue-50 text-blue-600">
                JSON
              </Badge>
            )}
            {response.is_json && response.obeys_schema === true && (
              <Badge variant="outline" className="bg-green-50 text-green-600 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Valid Schema
              </Badge>
            )}
            {response.is_json && response.obeys_schema === false && (
              <Badge variant="outline" className="bg-red-50 text-red-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> Invalid Schema
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {viewMode !== 'default' && (
              <Button variant="outline" size="sm" onClick={() => toggleViewMode('default')} title="Show Default View">
                <FileText className="h-3.5 w-3.5" />
              </Button>
            )}
            {viewMode !== 'raw' && (
              <Button variant="outline" size="sm" onClick={() => toggleViewMode('raw')} title="Show Raw Data">
                Raw
              </Button>
            )}
            {canShowFormView && viewMode !== 'form' && (
              <Button variant="outline" size="sm" onClick={() => toggleViewMode('form')} title="Show Form View">
                <FileJson className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button variant="outline" size="sm" title="Regenerate (Not Implemented)">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-red-600 hover:bg-red-50"
              onClick={handleDeleteResponse}
              disabled={isDeleting || isAnnotating}
              title="Delete Response"
            >
              {isDeleting ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {viewMode === 'raw' && (
          <div className="relative">
            <pre className="bg-gray-50 p-3 rounded-md overflow-auto text-xs font-mono">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        )}

        {viewMode === 'form' && canShowFormView && formData && activeSchema && (
          <div className="rjsf-shadcn p-4 border rounded-lg bg-white">
            <Form
              schema={activeSchema}
              formData={formData}
              validator={validator}
              uiSchema={uiSchema}
              templates={templates}
              widgets={widgets}
              disabled={true}
              onChange={() => {}}
              onSubmit={() => {}}
              onError={(errors: RJSFValidationError[]) => console.log("RJSF Errors:", errors)}
            >
              <div />
            </Form>
          </div>
        )}
        {viewMode === 'form' && (!canShowFormView || !formData) && (
          <div className="text-red-500 italic">Cannot display form view. Ensure response is valid JSON matching the schema and schema is loaded.</div>
        )}

        {viewMode === 'default' && (
          response.is_json ? (
            <JsonFormatter jsonString={response.content} />
          ) : (
            <div className="mb-4">
              <p className="whitespace-pre-wrap">{response.content}</p>
            </div>
          )
        )}
      </CardContent>

      <CardFooter className="border-t bg-gray-50 py-3 px-4 flex flex-col items-start gap-2">
        <div className="flex items-center gap-2 w-full">
          <Button
            variant="outline"
            size="sm"
            className="bg-blue-50 text-blue-600 hover:bg-blue-100"
            onClick={() => handleAnnotationSubmit(1)}
            disabled={isAnnotating}
          >
            <ThumbsUp className="h-4 w-4 mr-1" />
            Annotate with reward 1
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="bg-gray-100 text-gray-600 hover:bg-gray-200"
            onClick={() => handleAnnotationSubmit(0)}
            disabled={isAnnotating}
          >
            <ThumbsDown className="h-4 w-4 mr-1" />
            Annotate with reward 0
          </Button>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Check className="h-4 w-4 text-green-500" />
          </Button>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setHideAnnotations(!hideAnnotations)}>
              {hideAnnotations ? "Show Annotations" : "Hide Annotations"}
            </Button>
          </div>
        </div>

        {annotationError && <div className="text-red-500 text-sm">{annotationError}</div>}
        {deleteError && <div className="text-red-500 text-sm w-full">{deleteError}</div>}
        {annotationDeleteError && <div className="text-red-500 text-sm w-full">{annotationDeleteError}</div>}

        {!hideAnnotations && response.annotations.length > 0 && (
          <div className="w-full">
            {response.annotations.map((annotation) => (
              <div key={annotation.id} className="flex items-center justify-between py-1 border-t text-sm">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">Reward: {annotation.reward}</span>
                  <span className="text-gray-500">By: {annotation.by}</span>
                  <span className="text-gray-500">At: {new Date(annotation.at).toLocaleString()}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => handleDeleteAnnotation(annotation.id)}
                  disabled={deletingAnnotationId === annotation.id || isAnnotating}
                  title="Delete this annotation"
                >
                  {deletingAnnotationId === annotation.id ? (
                    <RefreshCw className="h-3.5 w-3.5 text-gray-500 animate-spin" />
                  ) : (
                    <X className="h-3.5 w-3.5 text-red-500" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}

        {!hideAnnotations && response.annotations.length === 0 && (
          <div className="w-full border-t pt-2 text-sm text-gray-500 italic">No annotations found.</div>
        )}
      </CardFooter>
    </Card>
  )
}
