import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import type { Spec } from "@/lib/types";
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
      toast.success("Spec gerada.");
      onDone(spec);
    },
    onError: (error) => toast.error(error.message),
  });
}

export function usePublishSpec(onDone: (spec: Spec) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.publishSpec,
    onSuccess: (spec) => {
      queryClient.invalidateQueries({ queryKey: ["specs", "list"] });
      toast.success("Issue publicada no GitHub.");
      onDone(spec);
    },
    onError: (error) => toast.error(error.message),
  });
}
