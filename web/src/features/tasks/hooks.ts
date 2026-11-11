import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import type { TaskFilters } from "@/lib/types";
import * as api from "./api";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function useTasks(filters: TaskFilters) {
  return useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => api.listTasks(filters),
    placeholderData: keepPreviousData,
  });
}

export function useSummary() {
  return useQuery({ queryKey: ["summary"], queryFn: api.getSummary });
}

export function useUsers() {
  return useQuery({ queryKey: ["users"], queryFn: api.listUsers, staleTime: 60_000 });
}

function useInvalidateTasks() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["summary"] });
  };
}

export function useCreateTask(onDone: () => void) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: api.createTask,
    onSuccess: () => {
      invalidate();
      toast.success("Task created.");
      onDone();
    },
    onError: (error) => toast.error(error.message),
  });
}

export function useUpdateTask(onDone: () => void) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: api.TaskPayload }) =>
      api.updateTask(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Task updated.");
      onDone();
    },
    onError: (error) => toast.error(error.message),
  });
}

export function useToggleTask() {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (task: { id: number; done: boolean }) =>
      task.done ? api.reopenTask(task.id) : api.completeTask(task.id),
    onSuccess: () => invalidate(),
    onError: (error) => toast.error(error.message),
  });
}

export function useDeleteTask() {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (id: number) => api.deleteTask(id),
    onSuccess: () => {
      invalidate();
      toast.success("Task deleted.");
    },
    onError: (error) => toast.error(error.message),
  });
}
