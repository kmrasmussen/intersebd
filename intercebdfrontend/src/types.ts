export interface CompletionsRequestDetailDto {
  id: string;
  request_log_id: string;
  intercept_key: string;
  messages: any[] | null;
  model: string | null;
  response_format: any | null;
  request_timestamp: string | null;
}

export interface CompletionResponseDetailDto {
  id: string;
  completion_request_id: string;
  annotation_target_id: string | null;
  provider: string | null;
  model: string | null;
  created: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  choice_finish_reason: string | null;
  choice_role: string | null;
  choice_content: string | null;
}

export interface CompletionPairDto {
  request: CompletionsRequestDetailDto; // Consider renaming to CompletionsRequestDetailDto for consistency
  response: CompletionResponseDetailDto | null; // <-- Allow null
}

export interface CompletionPairListResponseDto {
  pairs: CompletionPairDto[];
  intercept_key: string | null;
}

// From useCompletionAlternatives.ts (adjust if needed)
export interface AlternativeCompletionDto {
  id: string; // UUID from DB
  original_completion_request_id?: string; // Might be useful context
  annotation_target_id: string; // Should not be null if passed here
  alternative_content: string;
  created_at: string; // Or Date
  rater_id: string | null;
}

// The Discriminated Union
export type AnnotatableItemData =
  | (CompletionResponseDetailDto & { kind: 'response' })
  | (AlternativeCompletionDto & { kind: 'alternative' });
