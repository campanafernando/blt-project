import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-transparent px-[18px] py-3 text-[15px] font-medium leading-normal transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-[18px] [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "border-primary bg-primary text-primary-foreground hover:bg-primary-hover",
        outline: "border-border bg-card text-foreground hover:bg-soft",
        ghost: "text-muted-foreground hover:bg-soft hover:text-foreground",
        destructive: "border-destructive bg-destructive text-white hover:border-destructive-hover hover:bg-destructive-hover",
      },
      size: { default: "", sm: "px-3 py-2 text-[13px]", icon: "size-11 shrink-0 p-0" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  type = "button",
  title,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return (
    <button
      type={type}
      title={title ?? (size === "icon" ? props["aria-label"] : undefined)}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
