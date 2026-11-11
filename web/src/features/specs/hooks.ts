import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import type { Spec, SpecTasksRequest } from "@/lib/types";
import { useInvalidateTasks } from "@/features/tasks/hooks";
import * as api from "./api";

export function useSpecConfig() {
  return useQuery({ queryKey: ["specs", "config"], queryFn: api.getSpecConfig });
}

export function useSpecs() {
  return useQuery({ queryKey: ["specs", "list"], queryFn: api.listSpecs });
}

export function useCreateSpec(onDone: (spec: Spec) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createSpec,
    onSuccess: (spec) => {
      queryClient.invalidateQueries({ queryKey: ["specs", "list"] });
      toast.success("Spec generated.");
      onDone(spec);
    },
    onError: (error) => toast.error(error.message),
  });
}

// The dialog shows the server error itself, so no error toast here.
export function useCreateSpecTasks(specId: number, onDone: () => void) {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (payload: SpecTasksRequest) => api.createSpecTasks(specId, payload),
    onSuccess: ({ tasks }) => {
      invalidate();
      toast.success(tasks.length === 1 ? "1 task created." : `${tasks.length} tasks created.`);
      onDone();
    },
  });
}

export function usePublishSpec(onDone: (spec: Spec) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.publishSpec,
    onSuccess: (spec) => {
      queryClient.invalidateQueries({ queryKey: ["specs", "list"] });
      toast.success("Issue published.");
      onDone(spec);
    },
    onError: (error) => toast.error(error.message),
  });
}
