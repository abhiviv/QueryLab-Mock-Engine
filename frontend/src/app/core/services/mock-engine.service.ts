import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface MockRouteConfig {
  endpoint_path: string;
  http_method: string;
  target_table?: string;
  records_count: number;
  latency_ms: number;
}

export interface SandboxEnvironment {
  environment_name: string;
  db_connection_string?: string;
  routes: MockRouteConfig[];
  table_schemas?: Record<string, any[]>;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  path: string;
  method: string;
  target_table: string;
  latency_ms: number;
  status_code: number;
  response_size_bytes: number;
}

@Injectable({
  providedIn: 'root'
})
export class MockEngineService {
  private apiUrl = 'http://localhost:8000/api/sandbox';

  constructor(private http: HttpClient) {}

  inspectDatabase(dbConnectionString: string): Observable<{ success: boolean; tables: Record<string, any[]>; error: string | null }> {
    return this.http.post<{ success: boolean; tables: Record<string, any[]>; error: string | null }>(
      `${this.apiUrl}/inspect`,
      { db_connection_string: dbConnectionString }
    );
  }

  registerSandbox(env: SandboxEnvironment): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/register`, env);
  }

  getActiveSandbox(): Observable<{ active_sandbox: SandboxEnvironment | null; cached_tables: string[] }> {
    return this.http.get<{ active_sandbox: SandboxEnvironment | null; cached_tables: string[] }>(`${this.apiUrl}/active`);
  }

  getLogs(): Observable<LogEntry[]> {
    return this.http.get<LogEntry[]>(`${this.apiUrl}/logs`);
  }

  clearLogs(): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/logs/clear`, {});
  }

  previewRoute(route: MockRouteConfig, tableSchemas: Record<string, any[]>): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/preview`, {
      route,
      table_schemas: tableSchemas
    });
  }
}
