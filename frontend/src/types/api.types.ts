/**
 * Generic API response types.
 */

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
}
