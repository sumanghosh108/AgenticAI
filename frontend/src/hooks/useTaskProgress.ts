import { useState, useEffect, useCallback, useRef } from 'react';
import { TaskWebSocket } from '@/services/websocket';
import { decisionApi } from '@/api/client';
import type { WSMessage, TaskInfo, AgentInfo } from '@/types';

export interface TaskProgress {
  taskId: string | null;
  status: string;
  step: string;
  progress: number;
  error: string | null;
  result: Record<string, unknown> | null;
  isRunning: boolean;
  isComplete: boolean;
  query?: string;
  domain?: string;
  agents: AgentInfo[];
  totalAgents: number;
  completedAgents: number;
}

export function useTaskProgress(taskId: string | null) {
  const [progress, setProgress] = useState<TaskProgress>({
    taskId,
    status: 'idle',
    step: '',
    progress: 0,
    error: null,
    result: null,
    isRunning: false,
    isComplete: false,
    query: '',
    domain: '',
    agents: [],
    totalAgents: 0,
    completedAgents: 0,
  });

  const wsRef = useRef<TaskWebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket handler
  const handleWSMessage = useCallback((msg: WSMessage) => {
    setProgress((prev) => {
      if (msg.type === 'progress') {
        return {
          ...prev,
          status: msg.status || 'running',
          step: msg.step || prev.step,
          progress: msg.progress_pct || prev.progress,
          query: msg.details?.query || prev.query,
          domain: msg.details?.domain || prev.domain,
          isRunning: true,
          isComplete: false,
          agents: msg.details?.agents || prev.agents,
          totalAgents: msg.details?.total_agents ?? prev.totalAgents,
          completedAgents: msg.details?.completed_agents ?? prev.completedAgents,
        };
      }
      if (msg.type === 'completed') {
        return {
          ...prev,
          status: 'completed',
          progress: 100,
          result: msg.result as Record<string, unknown> || null,
          isRunning: false,
          isComplete: true,
        };
      }
      if (msg.type === 'error') {
        return {
          ...prev,
          status: 'failed',
          error: msg.error || 'Unknown error',
          isRunning: false,
          isComplete: true,
        };
      }
      return prev;
    });
  }, []);

  // Polling fallback
  const pollStatus = useCallback(async () => {
    if (!taskId) return;
    try {
      const resp = await decisionApi.getStatus(taskId);
      if (resp.success) {
        const info = resp as unknown as TaskInfo;
        setProgress((prev) => ({
          ...prev,
          taskId,
          status: info.status || prev.status,
          step: info.current_step || prev.step,
          progress: info.progress_pct ?? prev.progress,
          query: info.query || prev.query,
          domain: info.domain || prev.domain,
          error: info.error || null,
          isRunning: info.status === 'running' || info.status === 'queued',
          isComplete: info.status === 'completed' || info.status === 'failed',
          agents: info.agents || prev.agents,
          totalAgents: info.total_agents ?? prev.totalAgents,
          completedAgents: info.completed_agents ?? prev.completedAgents,
        }));

        if (info.status === 'completed' || info.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }
    } catch {
      // ignore polling errors
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;

    setProgress((prev) => ({
      ...prev,
      taskId,
      status: 'queued',
      step: '',
      progress: 0,
      error: null,
      result: null,
      isRunning: true,
      isComplete: false,
      query: '',
      domain: '',
      agents: [],
      totalAgents: 0,
      completedAgents: 0,
    }));

    // Try WebSocket first
    const ws = new TaskWebSocket(taskId);
    wsRef.current = ws;
    ws.onMessage(handleWSMessage);
    ws.connect();

    // Polling fallback every 3s
    pollRef.current = setInterval(pollStatus, 3000);
    pollStatus(); // immediate first check

    return () => {
      ws.disconnect();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [taskId, handleWSMessage, pollStatus]);

  return progress;
}
