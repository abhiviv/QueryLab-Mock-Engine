import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MockEngineService, MockRouteConfig, SandboxEnvironment, LogEntry } from '../../core/services/mock-engine.service';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  // Connection states
  environmentName = 'QueryLab_Local_Mock';
  dbConnectionString = 'sqlite:///backend/test_db.sqlite';
  
  // Reflection schema states
  inspectedTables: Record<string, any[]> = {};
  tableNames: string[] = [];
  selectedTable: string | null = null;
  
  // Custom mock route configuration states
  routes: MockRouteConfig[] = [];
  
  // Logs & status
  logs: LogEntry[] = [];
  activeSandbox: SandboxEnvironment | null = null;
  cachedTables: string[] = [];
  
  // UI states
  isInspectLoading = false;
  isDeployLoading = false;
  inspectError: string | null = null;
  deploySuccess: string | null = null;
  deployError: string | null = null;

  // Mock Override options
  mockOverrides = [
    { value: 'default', label: '-- Auto-Detect (Default) --' },
    { value: 'first_name', label: 'First Name' },
    { value: 'last_name', label: 'Last Name' },
    { value: 'full_name', label: 'Full Name' },
    { value: 'email', label: 'Email Address' },
    { value: 'username', label: 'Username' },
    { value: 'phone', label: 'Phone Number' },
    { value: 'address', label: 'Street Address' },
    { value: 'uuid', label: 'UUID / GUID' },
    { value: 'product', label: 'Product Name' },
    { value: 'category', label: 'Category' },
    { value: 'status', label: 'Status' },
    { value: 'token', label: 'Structured Token' },
    { value: 'currency', label: 'International Currency' },
    { value: 'age', label: 'Age (Integer)' },
    { value: 'quantity', label: 'Quantity / Count' },
    { value: 'year', label: 'Year (Integer)' },
    { value: 'price', label: 'Price / Cost' },
    { value: 'rating', label: 'Rating / Score' },
    { value: 'boolean', label: 'Boolean' },
    { value: 'date', label: 'Date (YYYY-MM-DD)' },
    { value: 'datetime', label: 'DateTime (ISO)' }
  ];

  // Preview states
  selectedPreviewRoute: MockRouteConfig | null = null;
  previewPayload: any = null;
  formattedPreviewPayload = '';
  isPreviewLoading = false;
  copySuccess = false;
  
  // Polling logs subscription
  private logPollSub?: Subscription;

  constructor(private mockService: MockEngineService) {}

  ngOnInit() {
    this.fetchActiveSandbox();
    this.startLogPolling();
  }

  ngOnDestroy() {
    if (this.logPollSub) {
      this.logPollSub.unsubscribe();
    }
  }

  // Poll server mock activity logs every 2 seconds
  startLogPolling() {
    this.logPollSub = interval(2000)
      .pipe(switchMap(() => this.mockService.getLogs()))
      .subscribe({
        next: (logs) => {
          this.logs = logs;
        },
        error: (err) => {
          console.error('Error polling mock engine logs:', err);
        }
      });
  }

  fetchActiveSandbox() {
    this.mockService.getActiveSandbox().subscribe({
      next: (res) => {
        if (res.active_sandbox) {
          this.activeSandbox = res.active_sandbox;
          this.environmentName = res.active_sandbox.environment_name;
          this.dbConnectionString = res.active_sandbox.db_connection_string || '';
          this.routes = res.active_sandbox.routes || [];
          this.cachedTables = res.cached_tables || [];
          
          if (res.active_sandbox.table_schemas && Object.keys(res.active_sandbox.table_schemas).length > 0) {
            this.inspectedTables = res.active_sandbox.table_schemas;
            this.tableNames = Object.keys(res.active_sandbox.table_schemas);
            if (this.tableNames.length > 0 && !this.selectedTable) {
              this.selectedTable = this.tableNames[0];
            }
          }
          
          // Auto select first route for preview if exists
          if (this.routes.length > 0 && !this.selectedPreviewRoute) {
            this.selectRouteForPreview(this.routes[0]);
          }
        }
      },
      error: (err) => {
        console.error('Could not fetch active simulation:', err);
      }
    });
  }

  inspectDb() {
    if (!this.dbConnectionString.trim()) {
      this.inspectError = 'Connection string cannot be empty.';
      return;
    }
    
    this.isInspectLoading = true;
    this.inspectError = null;
    
    this.mockService.inspectDatabase(this.dbConnectionString).subscribe({
      next: (res) => {
        this.isInspectLoading = false;
        if (res.success) {
          this.inspectedTables = res.tables;
          this.tableNames = Object.keys(res.tables);
          if (this.tableNames.length > 0) {
            this.selectedTable = this.tableNames[0];
            // Auto pre-populate a couple of demo routes if routes list is empty
            if (this.routes.length === 0) {
              this.routes = this.tableNames.slice(0, 2).map((t, idx) => ({
                endpoint_path: t,
                http_method: 'GET',
                target_table: t,
                records_count: idx === 0 ? 10 : 5,
                latency_ms: 150 + idx * 100
              }));
            }
          }
        } else {
          this.inspectError = res.error || 'Inspection failed.';
        }
      },
      error: (err) => {
        this.isInspectLoading = false;
        this.inspectError = err.error?.detail || err.message || 'Error connecting to daemon.';
      }
    });
  }

  selectActiveTable(table: string) {
    this.selectedTable = table;
  }

  addRouteRow() {
    // Default config values for a new route row
    this.routes.push({
      endpoint_path: 'api/resource',
      http_method: 'GET',
      target_table: this.tableNames.length > 0 ? this.tableNames[0] : undefined,
      records_count: 5,
      latency_ms: 200
    });
  }

  removeRouteRow(index: number) {
    this.routes.splice(index, 1);
  }

  deploySandbox() {
    if (!this.environmentName.trim()) {
      this.deployError = 'Sandbox environment name is required.';
      return;
    }

    this.isDeployLoading = true;
    this.deploySuccess = null;
    this.deployError = null;

    const payload: SandboxEnvironment = {
      environment_name: this.environmentName,
      db_connection_string: this.dbConnectionString || undefined,
      routes: this.routes,
      table_schemas: this.inspectedTables
    };

    this.mockService.registerSandbox(payload).subscribe({
      next: (res) => {
        this.isDeployLoading = false;
        this.deploySuccess = 'Mock simulation deployed and active!';
        this.fetchActiveSandbox();
        this.refreshLogs();
        setTimeout(() => this.deploySuccess = null, 5000);
      },
      error: (err) => {
        this.isDeployLoading = false;
        this.deployError = err.error?.detail || err.message || 'Failed to deploy simulation.';
      }
    });
  }

  selectRouteForPreview(route: MockRouteConfig) {
    this.selectedPreviewRoute = route;
    this.fetchPreview();
  }

  fetchPreview() {
    if (!this.selectedPreviewRoute) return;
    this.isPreviewLoading = true;
    this.mockService.previewRoute(this.selectedPreviewRoute, this.inspectedTables).subscribe({
      next: (data) => {
        this.isPreviewLoading = false;
        this.previewPayload = data;
        this.formattedPreviewPayload = this.syntaxHighlight(data);
      },
      error: (err) => {
        this.isPreviewLoading = false;
        this.previewPayload = null;
        this.formattedPreviewPayload = `<span class="json-error">Failed to generate preview: ${err.error?.detail || err.message}</span>`;
      }
    });
  }

  copyPreviewToClipboard() {
    if (!this.previewPayload) return;
    const jsonStr = JSON.stringify(this.previewPayload, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      this.copySuccess = true;
      setTimeout(() => this.copySuccess = false, 2000);
    });
  }

  syntaxHighlight(json: any): string {
    if (typeof json !== 'string') {
      json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, (match: string) => {
      let cls = 'json-number';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'json-key';
        } else {
          cls = 'json-string';
        }
      } else if (/true|false/.test(match)) {
        cls = 'json-boolean';
      } else if (/null/.test(match)) {
        cls = 'json-null';
      }
      return `<span class="${cls}">${match}</span>`;
    });
  }

  refreshLogs() {
    this.mockService.getLogs().subscribe({
      next: (logs) => this.logs = logs,
      error: (err) => console.error('Error fetching logs:', err)
    });
  }

  clearLogs() {
    this.mockService.clearLogs().subscribe({
      next: () => this.logs = [],
      error: (err) => console.error('Error clearing logs:', err)
    });
  }
}
