import { toast } from "sonner";

// API error type
export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export interface ApiResponse<T> {
  code: number;
  data: T;
  msg: string;
}

// request config interface
export interface RequestConfig {
  requiresAuth?: boolean;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export const getServerUrl = (endpoint: string) => {
  if (endpoint.startsWith("http")) return endpoint;

  return `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
};

class ApiClient {
  // default config
  private config: RequestConfig = {
    requiresAuth: true,
    headers: {
      "Content-Type": "application/json",
    },
  };

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message =
        errorData.message ||
        errorData.detail ||
        response.statusText ||
        `HTTP ${response.status}`;

      //TODO: Handle 401 unauthorized
      // if (response.status === 401) {
      //   localStorage.removeItem("authToken");
      //   if (typeof window !== "undefined") {
      //     window.location.href = "/login";
      //   }
      // }

      toast.error(message);

      throw new ApiError(message, response.status, errorData);
    }

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      return response.json();
    }

    return response.text() as unknown as T;
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: unknown,
    config: RequestConfig = {},
  ): Promise<T> {
    const mergedConfig = { ...this.config, ...config };
    const url = getServerUrl(endpoint);

    // add authentication header
    if (mergedConfig.requiresAuth) {
      const token = localStorage.getItem("authToken");
      if (token) {
        mergedConfig.headers!.Authorization = `Bearer ${token}`;
      }
    }

    // prepare request config
    const requestConfig: RequestInit = {
      method,
      headers: mergedConfig.headers,
      signal: mergedConfig.signal,
    };

    // add request body
    if (data && ["POST", "PUT", "PATCH"].includes(method)) {
      if (data instanceof FormData) {
        delete mergedConfig.headers!["Content-Type"];
        requestConfig.body = data;
      } else {
        requestConfig.body = JSON.stringify(data);
      }
    }

    const response = await fetch(url, requestConfig);
    return this.handleResponse<T>(response);
  }

  async get<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>("GET", endpoint, undefined, config);
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("POST", endpoint, data, config);
  }

  async put<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("PUT", endpoint, data, config);
  }

  async patch<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("PATCH", endpoint, data, config);
  }

  async delete<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>("DELETE", endpoint, undefined, config);
  }

  // file upload
  async upload<T>(
    endpoint: string,
    formData: FormData,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("POST", endpoint, formData, config);
  }
}

// default api client with authentication
export const apiClient = new ApiClient();
