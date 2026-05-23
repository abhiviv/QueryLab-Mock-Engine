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
      routes: this.routes
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
