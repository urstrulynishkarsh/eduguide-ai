import type { ApiErrorBody } from "@/lib/types";

/** The FastAPI backend. Only the Next.js server talks to it; the browser never does. */
export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * The error when the backend can't be reached (also sent by the routes that pass calls through). The
 * screens say it by its code (lib/copy `errors`); the message is for logs.
 */
export const UNREACHABLE: ApiErrorBody = {
  code: "unreachable",
  message: "The backend can't be reached.",
  details: null,
};

/** An error answer from the backend: `{"error": {"code", "message", "details"}}`. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody,
  ) {
    super(body.message);
  }
}

interface CallOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
}

/** One backend call. Throws ApiError, with status 0 when the backend can't be reached. */
export async function callBackend<T>(
  path: string,
  { method = "GET", body, token }: CallOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(API_BASE_URL + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, UNREACHABLE);
  }

  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      data?.error ?? { code: "internal_error", message: "The backend's answer was not JSON.", details: null },
    );
  }
  return data as T;
}
